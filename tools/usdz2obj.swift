import Foundation
import ModelIO

// USDZ -> OBJ (+ .mtl + textures) so Python can read the colour.
guard CommandLine.arguments.count >= 3 else {
    FileHandle.standardError.write("usage: usdz2obj <in.usdz> <out.obj>\n".data(using: .utf8)!)
    exit(2)
}
let inURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outURL = URL(fileURLWithPath: CommandLine.arguments[2])

let asset = MDLAsset(url: inURL)
asset.loadTextures()
guard asset.count > 0 else { print("no objects"); exit(1) }
try? FileManager.default.createDirectory(at: outURL.deletingLastPathComponent(),
                                         withIntermediateDirectories: true)
do {
    try asset.export(to: outURL)
    print("exported: \(outURL.lastPathComponent)")
    let dir = outURL.deletingLastPathComponent()
    let files = (try? FileManager.default.contentsOfDirectory(atPath: dir.path)) ?? []
    for f in files.sorted() { print("  \(f)") }
} catch {
    print("export failed: \(error)"); exit(1)
}
