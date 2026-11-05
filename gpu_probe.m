#import <UIKit/UIKit.h>
#import <Metal/Metal.h>

@interface ProbeDelegate : UIResponder <UIApplicationDelegate>
@property(nonatomic,strong) UIWindow *window;
@end
@implementation ProbeDelegate
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options {
    self.window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
    UIViewController *vc = [UIViewController new]; vc.view.backgroundColor = UIColor.blackColor;
    UILabel *label = [[UILabel alloc] initWithFrame:CGRectMake(80,80,1700,850)];
    label.textColor = UIColor.whiteColor; label.font = [UIFont systemFontOfSize:30]; label.numberOfLines = 0;
    label.text = @"Checking Apple TV graphics compatibility..."; [vc.view addSubview:label];
    self.window.rootViewController = vc; [self.window makeKeyAndVisible];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0), ^{
        @autoreleasepool {
            id<MTLDevice> device = MTLCreateSystemDefaultDevice();
            NSMutableDictionary *report = [NSMutableDictionary dictionary];
            report[@"device"] = device.name ?: @"none";
            report[@"apple7"] = @([device supportsFamily:MTLGPUFamilyApple7]);
            report[@"argument_buffer_tier"] = @(device.argumentBuffersSupport);
            report[@"bc_compression"] = @(device.supportsBCTextureCompression);
            id<MTLBuffer> output = [device newBufferWithLength:4096 options:MTLResourceStorageModeShared];
            report[@"buffer_gpu_address"] = @(output.gpuAddress != 0);
            MTLTextureDescriptor *td = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm width:4 height:4 mipmapped:NO];
            id<MTLTexture> texture = [device newTextureWithDescriptor:td];
            report[@"texture_resource_id"] = @(texture.gpuResourceID._impl != 0);
            NSMutableArray *tests = [NSMutableArray array];
            NSString *source = @"#include <metal_stdlib>\nusing namespace metal;\nstruct Args { device uint* output; };\nkernel void check(constant Args& args [[buffer(0)]],uint tid [[thread_position_in_grid]]) { if(tid==0) args.output[0]=0x1234abcd; }";
            for (NSNumber *version in @[@(MTLLanguageVersion2_2),@(MTLLanguageVersion2_4),@(MTLLanguageVersion3_0)]) {
                NSMutableDictionary *test = [NSMutableDictionary dictionaryWithObject:version forKey:@"language_version"];
                MTLCompileOptions *co = [MTLCompileOptions new]; co.languageVersion = version.unsignedIntegerValue;
                NSError *error = nil; id<MTLLibrary> library = [device newLibraryWithSource:source options:co error:&error];
                if (!library) { test[@"error"] = error.localizedDescription ?: @"library failed"; [tests addObject:test]; continue; }
                id<MTLComputePipelineState> pipeline = [device newComputePipelineStateWithFunction:[library newFunctionWithName:@"check"] error:&error];
                if (!pipeline) { test[@"error"] = error.localizedDescription ?: @"pipeline failed"; [tests addObject:test]; continue; }
                memset(output.contents,0,4096); uint64_t address = output.gpuAddress;
                id<MTLCommandQueue> queue = [device newCommandQueue]; id<MTLCommandBuffer> cb = [queue commandBuffer];
                id<MTLComputeCommandEncoder> en = [cb computeCommandEncoder]; [en setComputePipelineState:pipeline];
                [en setBytes:&address length:sizeof address atIndex:0]; [en useResource:output usage:MTLResourceUsageWrite];
                [en dispatchThreadgroups:MTLSizeMake(1,1,1) threadsPerThreadgroup:MTLSizeMake(1,1,1)];
                [en endEncoding]; [cb commit]; [cb waitUntilCompleted];
                test[@"raw_pointer_dispatch_passed"] = @(*(uint32_t *)output.contents == 0x1234abcd);
                if (cb.error) test[@"error"] = cb.error.localizedDescription;
                [tests addObject:test];
            }
            report[@"tests"] = tests;
            NSData *data = [NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil];
            NSString *cache = NSSearchPathForDirectoriesInDomains(NSCachesDirectory,NSUserDomainMask,YES).firstObject;
            [data writeToFile:[cache stringByAppendingPathComponent:@"gpu-probe.json"] atomically:YES];
            NSString *text = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
            dispatch_async(dispatch_get_main_queue(), ^{ label.text = text; });
        }
    });
    return YES;
}
@end
int main(int argc,char **argv) { @autoreleasepool { return UIApplicationMain(argc,argv,nil,NSStringFromClass(ProbeDelegate.class)); } }
