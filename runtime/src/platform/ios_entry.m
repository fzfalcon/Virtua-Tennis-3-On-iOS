/* iOS application entry for the recompiled game.
 * SDL3 provides the UIKit application loop through SDL_main.h. The game executable and shader
 * pack are bundled resources; the extracted retail data is supplied by the owner under Documents/data2.
 */
#import <Foundation/Foundation.h>
#include <SDL3/SDL_main.h>
#include "vt3rt.h"

#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    @autoreleasepool {
        NSString *resources = [[NSBundle mainBundle] resourcePath];
        NSString *documents = [NSHomeDirectory() stringByAppendingPathComponent:@"Documents"];
        NSString *dataRoot = [documents stringByAppendingPathComponent:@"data2"];
        NSString *imagePath = [resources stringByAppendingPathComponent:@"image.bin"];
        NSString *shaderPath = [resources stringByAppendingPathComponent:@"shaders.pack"];

        if (!resources || !imagePath || !shaderPath) {
            NSLog(@"VT3: application resources are missing");
            return 2;
        }
        /* The Documents directory is exposed in Apple's Files app through Info.plist. */
        [[NSFileManager defaultManager] createDirectoryAtPath:documents
                                  withIntermediateDirectories:YES attributes:nil error:nil];
        setenv("VT3_GAME_ROOT", [dataRoot fileSystemRepresentation], 1);
        setenv("VT3_SHADER_PACK", [shaderPath fileSystemRepresentation], 1);
        setenv("VT3_RENDERER", "vulkan", 1); /* Vulkan is provided by MoltenVK over Metal. */
        setenv("VT3_TOUCH", "1", 1);
        chdir([resources fileSystemRepresentation]);

        if (![[NSFileManager defaultManager] fileExistsAtPath:imagePath]) {
            NSLog(@"VT3: bundled image.bin is missing");
            return 3;
        }
        if (![[NSFileManager defaultManager] fileExistsAtPath:shaderPath]) {
            NSLog(@"VT3: bundled shaders.pack is missing");
            return 4;
        }
        BOOL isDir = NO;
        if (![[NSFileManager defaultManager] fileExistsAtPath:dataRoot isDirectory:&isDir] || !isDir) {
            NSLog(@"VT3: create Documents/data2 and copy your legally obtained, extracted game data into it.");
        }
        return vt3_run(&vt3_mod, [imagePath fileSystemRepresentation]);
    }
}
