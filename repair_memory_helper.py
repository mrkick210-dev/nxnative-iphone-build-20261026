"""Correct the public helper's header fetch without embedding any user's data."""
from pathlib import Path
import re,plistlib
r=Path('helper');p=r/'GetMoreRam/AnisetteDataHelper.swift';s=p.read_text()
start=s.index('    func getAnisetteData(refresh: Bool = false)')
end=s.index('    // MARK: - COMMON',start)
replacement='''    func getAnisetteData(refresh: Bool = false) async throws -> AnisetteData {
        let file = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("signing-provider.txt")
        guard let value = try? String(contentsOf: file, encoding: .utf8),
              let endpoint = URL(string: value.trimmingCharacters(in: .whitespacesAndNewlines)),
              endpoint.scheme == "https", endpoint.host == "sideloadly.io",
              endpoint.user == nil, endpoint.password == nil, endpoint.query == nil else {
            throw "The approved signing-header provider has not been configured."
        }
        // The provider receives only an empty GET, never Apple credentials.
        var request = URLRequest(url: endpoint)
        request.timeoutInterval = 30
        request.cachePolicy = .reloadIgnoringLocalCacheData
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw "The signing-header provider did not return a successful response."
        }
        return try await self.extractAnisetteData(data, http, v3: false)
    }

'''
s=s[:start]+replacement+s[end:]
# Do not display signing-header secrets in the on-device debug log.
s=s.replace('self.printOut("Anisette used: \\(formattedJSON)")','self.printOut("Signing headers received")').replace('self.printOut("Original JSON: \\(json)")','')
p.write_text(s)
project=r/'GetMoreRam.xcodeproj/project.pbxproj';v=project.read_text();v=v.replace('CURRENT_PROJECT_VERSION = 1;', 'CURRENT_PROJECT_VERSION = 2;')
v=v.replace('CURRENT_PROJECT_VERSION = 2;', 'CURRENT_PROJECT_VERSION = 3;')
v=v.replace('INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;', 'INFOPLIST_KEY_UIFileSharingEnabled = YES;\n\t\t\t\tINFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;')
project.write_text(v)
model=r/'GetMoreRam/AppIDViewModel.swift';m=model.read_text()
old='''        let cool = try await AppleAPI.shared.updateAppID(appID, capabilities: ["INCREASED_MEMORY_LIMIT"], team: team, session: session)
        
        result = "\\(cool)"'''
new='''        // Anisette headers are time-sensitive: obtain fresh data for this request.
        session.anisetteData = try await AnisetteDataHelper.shared.getAnisetteData(refresh: true)
        let ani = session.anisetteData
        let capability: [String: Any] = [
            "type": "bundleIdCapabilities",
            "attributes": ["enabled": true, "settings": []],
            "relationships": ["capability": ["data": ["id": "INCREASED_MEMORY_LIMIT", "type": "capabilities"]]]
        ]
        let body: [String: Any] = ["data": [
            "id": appID.identifier, "type": "bundleIds",
            "attributes": ["name": appID.name, "identifier": appID.bundleIdentifier,
                           "teamId": team.identifier, "seedId": team.identifier,
                           "bundleType": "bundle", "hasExclusiveManagedCapabilities": false],
            "relationships": ["bundleIdCapabilities": ["data": [capability]]]
        ]]
        let endpoint = URL(string: "https://developerservices2.apple.com/services/v1/bundleIds/")!.appendingPathComponent(appID.identifier)
        var request = URLRequest(url: endpoint)
        request.httpMethod = "PATCH"
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        request.timeoutInterval = 30
        let headers = [
            "Content-Type": "application/vnd.api+json", "Accept": "application/vnd.api+json",
            "User-Agent": "Xcode", "Accept-Language": "en-us",
            "X-Apple-App-Info": "com.apple.gs.xcode.auth", "X-Xcode-Version": "11.2 (11B41)",
            "X-Apple-I-Identity-Id": session.dsid, "X-Apple-GS-Token": session.authToken,
            "X-Apple-I-MD-M": ani.machineID, "X-Apple-I-MD": ani.oneTimePassword,
            "X-Apple-I-MD-LU": ani.localUserID, "X-Apple-I-MD-RINFO": String(ani.routingInfo),
            "X-Mme-Device-Id": ani.deviceUniqueIdentifier, "X-MMe-Client-Info": ani.deviceDescription,
            "X-Apple-I-Client-Time": ISO8601DateFormatter().string(from: Date()),
            "X-Apple-Locale": ani.locale.identifier,
            "X-Apple-I-TimeZone": ani.timeZone.abbreviation() ?? "GMT"
        ]
        for (key, value) in headers { request.setValue(value, forHTTPHeaderField: key) }
        let (data, response) = try await AppleAPI.shared.session.data(for: request)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
        let errors = (json["errors"] as? [[String: Any]] ?? []).map { error in
            [error["code"], error["title"], error["detail"]].compactMap { $0 as? String }.joined(separator: ": ")
        }.joined(separator: "; ")
        let success = (200..<300).contains(status) && json["data"] is [String: Any]
        let diagnostic: [String: Any] = ["http_status": status, "success": success,
            "bundle_id": appID.bundleIdentifier, "response_keys": Array(json.keys).sorted(),
            "apple_error": errors, "date": ISO8601DateFormatter().string(from: Date())]
        let file = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("capability-result.json")
        try? JSONSerialization.data(withJSONObject: diagnostic, options: .sortedKeys).write(to: file, options: .atomic)
        guard success else {
            let detail = errors.isEmpty ? "Apple returned HTTP \\(status); response fields: \\(json.keys.sorted().joined(separator: ", "))" : errors
            throw "Memory capability was not confirmed: " + detail
        }
        await MainActor.run { result = "Increased Memory Limit enabled. Reinstall the game to apply it." }'''
assert old in m,'Official capability method changed'
m=m.replace(old,new,1)
m=m.replace('        let ids = try await AppleAPI.shared.fetchAppIDsForTeam', '        session.anisetteData = try await AnisetteDataHelper.shared.getAnisetteData(refresh: true)\n        let ids = try await AppleAPI.shared.fetchAppIDsForTeam',1)
model.write_text(m)
print('Patched fresh header fetch, capability request and redacted error handling; no account/provider URL embedded.')
