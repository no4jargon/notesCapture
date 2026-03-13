import AppKit
import Foundation
import Darwin

final class NotePanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { true }
}

final class NoteTextView: NSTextView {
    var saveHandler: (() -> Void)?
    var bulletHandler: (() -> Void)?
    var cancelHandler: (() -> Void)?

    override func keyDown(with event: NSEvent) {
        let modifiers = event.modifierFlags.intersection(.deviceIndependentFlagsMask)

        if modifiers == [.command], event.keyCode == 36 {
            saveHandler?()
            return
        }

        if modifiers == [.command, .shift], event.charactersIgnoringModifiers == "7" {
            bulletHandler?()
            return
        }

        if modifiers.isEmpty, event.keyCode == 53 {
            cancelHandler?()
            return
        }

        super.keyDown(with: event)
    }

    override func insertNewline(_ sender: Any?) {
        guard selectedRange().length == 0 else {
            super.insertNewline(sender)
            return
        }

        let context = currentLineContext()
        if let prefix = context.bulletPrefix {
            if context.trimmedLine == prefix.trimmingCharacters(in: .whitespaces) {
                insertText("\n", replacementRange: selectedRange())
            } else {
                insertText("\n\(prefix)", replacementRange: selectedRange())
            }
            return
        }

        super.insertNewline(sender)
    }

    private func currentLineContext() -> (trimmedLine: String, bulletPrefix: String?) {
        let nsString = string as NSString
        guard nsString.length > 0 else { return ("", nil) }

        let cursorLocation = min(selectedRange().location, max(nsString.length - 1, 0))
        let lineRange = nsString.lineRange(for: NSRange(location: cursorLocation, length: 0))
        let rawLine = nsString.substring(with: lineRange)
        let line = rawLine.trimmingCharacters(in: .newlines)

        return (line, bulletPrefix(for: line))
    }

    private func bulletPrefix(for line: String) -> String? {
        let indentation = String(line.prefix { $0 == " " || $0 == "\t" })
        let trimmed = String(line.dropFirst(indentation.count))

        for marker in ["• ", "- ", "* "] {
            if trimmed.hasPrefix(marker) {
                return indentation + marker
            }
        }

        return nil
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    private let dataDirectoryURL: URL
    private let notesFileURL: URL
    private let entriesDirectoryURL: URL
    private let inboxDirectoryURL: URL

    private let timestampFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        return formatter
    }()

    private let filenameTimestampFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd_HH-mm-ss"
        return formatter
    }()

    private var panel: NotePanel!
    private var textView: NoteTextView!

    init(dataDirectoryURL: URL) {
        self.dataDirectoryURL = dataDirectoryURL
        self.notesFileURL = dataDirectoryURL.appendingPathComponent("notes.txt")
        self.entriesDirectoryURL = dataDirectoryURL.appendingPathComponent("entries", isDirectory: true)
        self.inboxDirectoryURL = dataDirectoryURL.appendingPathComponent("inbox", isDirectory: true)
        super.init()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        do {
            try prepareStorage()
        } catch {
            let alert = NSAlert(error: error)
            alert.runModal()
            NSApp.terminate(nil)
            return
        }
        buildUI()
        showWindow()
    }

    func applicationDidResignActive(_ notification: Notification) {
        panel?.close()
    }

    func windowWillClose(_ notification: Notification) {
        NSApp.terminate(nil)
    }

    private func buildUI() {
        panel = NotePanel(
            contentRect: NSRect(x: 0, y: 0, width: 460, height: 280),
            styleMask: [.titled, .closable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        panel.delegate = self
        panel.titleVisibility = .hidden
        panel.titlebarAppearsTransparent = true
        panel.level = .floating
        panel.isFloatingPanel = true
        panel.isReleasedWhenClosed = false
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .transient]
        panel.standardWindowButton(.miniaturizeButton)?.isHidden = true
        panel.standardWindowButton(.zoomButton)?.isHidden = true

        let contentView = NSView(frame: panel.contentRect(forFrameRect: panel.frame))
        contentView.translatesAutoresizingMaskIntoConstraints = false
        panel.contentView = contentView

        let titleLabel = NSTextField(labelWithString: "Quick note")
        titleLabel.font = .systemFont(ofSize: 16, weight: .semibold)
        titleLabel.translatesAutoresizingMaskIntoConstraints = false

        let subtitleLabel = NSTextField(labelWithString: "Enter = newline • ⌘↩ = save • ⌘⇧7 = bullets • Esc = close")
        subtitleLabel.font = .systemFont(ofSize: 11)
        subtitleLabel.textColor = .secondaryLabelColor
        subtitleLabel.translatesAutoresizingMaskIntoConstraints = false

        let scrollView = NSScrollView()
        scrollView.translatesAutoresizingMaskIntoConstraints = false
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .bezelBorder
        scrollView.drawsBackground = true
        scrollView.backgroundColor = .textBackgroundColor

        let textStorage = NSTextStorage()
        let layoutManager = NSLayoutManager()
        let textContainer = NSTextContainer(size: NSSize(width: 420, height: CGFloat.greatestFiniteMagnitude))
        textContainer.widthTracksTextView = true
        textContainer.heightTracksTextView = false
        textContainer.lineBreakMode = .byWordWrapping
        textContainer.lineFragmentPadding = 0
        textStorage.addLayoutManager(layoutManager)
        layoutManager.addTextContainer(textContainer)

        textView = NoteTextView(frame: NSRect(x: 0, y: 0, width: 420, height: 180), textContainer: textContainer)
        textView.font = .systemFont(ofSize: 14)
        textView.textColor = .labelColor
        textView.backgroundColor = .textBackgroundColor
        textView.insertionPointColor = .labelColor
        textView.drawsBackground = true
        textView.isRichText = false
        textView.importsGraphics = false
        textView.allowsUndo = true
        textView.isAutomaticQuoteSubstitutionEnabled = false
        textView.minSize = NSSize(width: 0, height: 0)
        textView.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        textView.isHorizontallyResizable = false
        textView.isVerticallyResizable = true
        textView.autoresizingMask = [.width]
        textView.textContainerInset = NSSize(width: 10, height: 10)
        textView.saveHandler = { [weak self] in self?.saveAndQuit() }
        textView.bulletHandler = { [weak self] in self?.toggleBullets() }
        textView.cancelHandler = { [weak self] in self?.panel.close() }
        scrollView.documentView = textView

        let bulletButton = NSButton(title: "• Bullet", target: self, action: #selector(toggleBulletsAction))
        bulletButton.bezelStyle = .rounded
        bulletButton.translatesAutoresizingMaskIntoConstraints = false

        let saveButton = NSButton(title: "Save", target: self, action: #selector(saveAction))
        saveButton.bezelStyle = .rounded
        saveButton.keyEquivalent = "\r"
        saveButton.keyEquivalentModifierMask = [.command]
        saveButton.translatesAutoresizingMaskIntoConstraints = false

        contentView.addSubview(titleLabel)
        contentView.addSubview(subtitleLabel)
        contentView.addSubview(scrollView)
        contentView.addSubview(bulletButton)
        contentView.addSubview(saveButton)

        NSLayoutConstraint.activate([
            titleLabel.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 18),
            titleLabel.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 18),

            subtitleLabel.topAnchor.constraint(equalTo: titleLabel.bottomAnchor, constant: 4),
            subtitleLabel.leadingAnchor.constraint(equalTo: titleLabel.leadingAnchor),
            subtitleLabel.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -18),

            scrollView.topAnchor.constraint(equalTo: subtitleLabel.bottomAnchor, constant: 12),
            scrollView.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 18),
            scrollView.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -18),
            scrollView.bottomAnchor.constraint(equalTo: bulletButton.topAnchor, constant: -14),

            bulletButton.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 18),
            bulletButton.bottomAnchor.constraint(equalTo: contentView.bottomAnchor, constant: -18),

            saveButton.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -18),
            saveButton.centerYAnchor.constraint(equalTo: bulletButton.centerYAnchor)
        ])
    }

    private func showWindow() {
        guard let screen = NSScreen.main ?? NSScreen.screens.first else { return }
        let visibleFrame = screen.visibleFrame
        let size = panel.frame.size
        let origin = NSPoint(
            x: visibleFrame.midX - size.width / 2,
            y: visibleFrame.maxY - size.height - 80
        )

        panel.setFrameOrigin(origin)
        panel.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        panel.layoutIfNeeded()
        if let contentWidth = panel.contentView?.bounds.width {
            let textWidth = max(contentWidth - 36, 100)
            textView.frame.size.width = textWidth
            textView.textContainer?.containerSize = NSSize(width: textWidth, height: CGFloat.greatestFiniteMagnitude)
        }
        panel.makeFirstResponder(textView)
    }

    @objc private func saveAction() {
        saveAndQuit()
    }

    @objc private func toggleBulletsAction() {
        toggleBullets()
    }

    private func saveAndQuit() {
        let text = normalize(textView.string)
        guard !text.isEmpty else {
            NSSound.beep()
            return
        }

        do {
            try saveEntry(text: text, source: "mac-hotkey")
            try materializeNotes()
            panel.close()
        } catch {
            let alert = NSAlert(error: error)
            alert.runModal()
        }
    }

    private func toggleBullets() {
        let nsString = textView.string as NSString
        let selection = textView.selectedRange()

        if nsString.length == 0 {
            textView.insertText("• ", replacementRange: selection)
            return
        }

        let targetRange: NSRange
        if selection.length == 0 {
            let safeLocation = min(selection.location, max(nsString.length - 1, 0))
            targetRange = nsString.lineRange(for: NSRange(location: safeLocation, length: 0))
        } else {
            targetRange = nsString.lineRange(for: selection)
        }

        let selectedText = nsString.substring(with: targetRange)
        let lines = selectedText.split(separator: "\n", omittingEmptySubsequences: false).map(String.init)
        let removeBullets = lines.filter { !$0.isEmpty }.allSatisfy { bulletMarkerRange(in: $0) != nil }

        let transformed = lines.map { line -> String in
            guard !line.isEmpty else { return line }
            if removeBullets, let range = bulletMarkerRange(in: line) {
                var updated = line
                updated.removeSubrange(range)
                return updated
            }

            let indentation = String(line.prefix { $0 == " " || $0 == "\t" })
            let content = String(line.dropFirst(indentation.count))
            return indentation + "• " + content
        }.joined(separator: "\n")

        textView.textStorage?.replaceCharacters(in: targetRange, with: transformed)
        textView.setSelectedRange(NSRange(location: targetRange.location, length: (transformed as NSString).length))
    }

    private func bulletMarkerRange(in line: String) -> Range<String.Index>? {
        let indentationEnd = line.firstIndex { $0 != " " && $0 != "\t" } ?? line.endIndex
        let tail = line[indentationEnd...]

        for marker in ["• ", "- ", "* "] {
            if tail.hasPrefix(marker) {
                return indentationEnd..<line.index(indentationEnd, offsetBy: marker.count)
            }
        }

        return nil
    }

    private func normalize(_ text: String) -> String {
        text.replacingOccurrences(of: "\r\n", with: "\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func prepareStorage() throws {
        try FileManager.default.createDirectory(at: dataDirectoryURL, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: entriesDirectoryURL, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: inboxDirectoryURL, withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: notesFileURL.path) {
            FileManager.default.createFile(atPath: notesFileURL.path, contents: nil)
        }
    }

    private func saveEntry(text: String, source: String) throws {
        let now = Date()
        let calendar = Calendar.current
        let year = calendar.component(.year, from: now)
        let month = calendar.component(.month, from: now)
        let day = calendar.component(.day, from: now)

        let dayDirectoryURL = entriesDirectoryURL
            .appendingPathComponent(String(format: "%04d", year), isDirectory: true)
            .appendingPathComponent(String(format: "%02d", month), isDirectory: true)
            .appendingPathComponent(String(format: "%02d", day), isDirectory: true)

        try FileManager.default.createDirectory(at: dayDirectoryURL, withIntermediateDirectories: true)

        let timestamp = filenameTimestampFormatter.string(from: now)
        let deviceName = sanitize(Host.current().localizedName ?? "mac")
        let safeSource = sanitize(source)
        let uniqueID = String(UUID().uuidString.prefix(8)).lowercased()
        let filename = "\(timestamp)--\(safeSource)--\(deviceName)--\(uniqueID).txt"
        let fileURL = dayDirectoryURL.appendingPathComponent(filename)

        try writeAtomically(text: text + "\n", to: fileURL, exclusive: true)
    }

    private func materializeNotes() throws {
        let entries = try entryFileURLs()
        var output = ""

        for entryURL in entries {
            let text = try String(contentsOf: entryURL, encoding: .utf8)
                .trimmingCharacters(in: .whitespacesAndNewlines)

            guard !text.isEmpty else { continue }

            let displayTimestamp = displayTimestamp(for: entryURL.lastPathComponent)
            output += "[\(displayTimestamp)]\n\(text)\n\n"
        }

        try writeAtomically(text: output, to: notesFileURL, exclusive: false)
    }

    private func entryFileURLs() throws -> [URL] {
        guard FileManager.default.fileExists(atPath: entriesDirectoryURL.path) else { return [] }

        let enumerator = FileManager.default.enumerator(
            at: entriesDirectoryURL,
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        )

        var files: [URL] = []
        while let url = enumerator?.nextObject() as? URL {
            let values = try url.resourceValues(forKeys: [.isRegularFileKey])
            if values.isRegularFile == true, url.pathExtension.lowercased() == "txt" {
                files.append(url)
            }
        }

        return files.sorted { $0.path < $1.path }
    }

    private func displayTimestamp(for filename: String) -> String {
        let prefix = filename.components(separatedBy: "--").first ?? filename.replacingOccurrences(of: ".txt", with: "")
        if let date = filenameTimestampFormatter.date(from: prefix) {
            return timestampFormatter.string(from: date)
        }
        return prefix.replacingOccurrences(of: "_", with: " ")
    }

    private func sanitize(_ value: String) -> String {
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_"))
        let scalars = value.unicodeScalars.map { allowed.contains($0) ? Character($0) : "-" }
        let collapsed = String(scalars)
            .replacingOccurrences(of: "--+", with: "-", options: .regularExpression)
            .trimmingCharacters(in: CharacterSet(charactersIn: "-"))
        return collapsed.isEmpty ? "unknown" : collapsed
    }

    private func writeAtomically(text: String, to url: URL, exclusive: Bool) throws {
        let path = url.path
        let flags = exclusive ? (O_WRONLY | O_CREAT | O_EXCL) : (O_WRONLY | O_CREAT | O_TRUNC)
        let fd = open(path, flags, S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH)

        guard fd != -1 else {
            throw NSError(domain: NSPOSIXErrorDomain, code: Int(errno))
        }

        defer { close(fd) }

        let data = Data(text.utf8)
        let result = data.withUnsafeBytes { buffer in
            write(fd, buffer.baseAddress, buffer.count)
        }

        if result == -1 || result != data.count {
            throw NSError(domain: NSPOSIXErrorDomain, code: Int(errno))
        }
    }
}

let dataPath = CommandLine.arguments.dropFirst().first ?? FileManager.default.currentDirectoryPath
let dataURL = URL(fileURLWithPath: dataPath, isDirectory: true)

let app = NSApplication.shared
let delegate = AppDelegate(dataDirectoryURL: dataURL)
app.delegate = delegate
app.run()
