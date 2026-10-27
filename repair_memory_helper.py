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
v=v.replace('INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;', 'INFOPLIST_KEY_UIFileSharingEnabled = YES;\n\t\t\t\tINFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;')
project.write_text(v)
print('Patched header fetch; no account or private provider URL embedded.')
