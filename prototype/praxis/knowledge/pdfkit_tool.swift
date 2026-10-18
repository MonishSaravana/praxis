// Local PDF text + outline extraction and page rendering with macOS PDFKit (no Python package needed).
// Built once by praxis/knowledge/parse.py into cache/bin/praxis-pdfkit. Nothing leaves the machine.
//   praxis-pdfkit text <file.pdf>                      -> JSON {"title", "pages": [text...], "outline": [{title, level, page}]}
//   praxis-pdfkit render <file.pdf> <page> <out.png> <max_side>   (page is 1-based)
import AppKit
import Foundation
import PDFKit

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(1)
}

let args = CommandLine.arguments
if args.count < 3 { fail("usage: praxis-pdfkit text|render <file.pdf> ...") }
guard let doc = PDFDocument(url: URL(fileURLWithPath: args[2])) else { fail("cannot open PDF") }
if doc.isLocked { fail("PDF is password-protected") }

if args[1] == "text" {
    var pages: [String] = []
    for i in 0..<doc.pageCount {
        pages.append(doc.page(at: i)?.string ?? "")
    }
    var outline: [[String: Any]] = []
    func walk(_ node: PDFOutline, _ level: Int) {
        for i in 0..<node.numberOfChildren {
            guard let c = node.child(at: i) else { continue }
            var page = 0
            if let p = c.destination?.page { page = doc.index(for: p) + 1 }
            outline.append(["title": c.label ?? "", "level": level, "page": page])
            walk(c, level + 1)
        }
    }
    if let root = doc.outlineRoot { walk(root, 1) }
    let title = (doc.documentAttributes?[PDFDocumentAttribute.titleAttribute] as? String) ?? ""
    let out: [String: Any] = ["title": title, "pages": pages, "outline": outline]
    let data = try! JSONSerialization.data(withJSONObject: out, options: [])
    FileHandle.standardOutput.write(data)
} else if args[1] == "render" {
    if args.count < 6 { fail("usage: praxis-pdfkit render <file.pdf> <page> <out.png> <max_side>") }
    guard let n = Int(args[3]), n >= 1, n <= doc.pageCount, let page = doc.page(at: n - 1) else { fail("bad page") }
    let side = CGFloat(Double(args[5]) ?? 1200)
    let img = page.thumbnail(of: CGSize(width: side, height: side), for: .mediaBox)
    guard let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
          let png = rep.representation(using: .png, properties: [:]) else { fail("render failed") }
    try! png.write(to: URL(fileURLWithPath: args[4]))
} else {
    fail("unknown command")
}
