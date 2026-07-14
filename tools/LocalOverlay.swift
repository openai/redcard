import Cocoa
import Darwin

func acquireDemoOverlayLock() -> Int32? {
    let lockPath = (NSTemporaryDirectory() as NSString).appendingPathComponent("redcard-demo-overlay.lock")
    let descriptor = open(lockPath, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
    guard descriptor >= 0 else { return nil }
    guard flock(descriptor, LOCK_EX | LOCK_NB) == 0 else {
        close(descriptor)
        return nil
    }
    return descriptor
}

func processIsRunning(_ pid: pid_t) -> Bool {
    guard pid > 1 else { return true }
    if kill(pid, 0) == 0 { return true }
    return errno != ESRCH
}

func overlayScreens() -> [NSScreen] {
    NSScreen.screens.isEmpty ? [NSScreen.main].compactMap { $0 } : NSScreen.screens
}

func overlayTopLeftReferenceY(screens: [NSScreen]) -> CGFloat {
    let primary = screens.first { $0.frame.origin == .zero } ?? screens.first
    return primary?.frame.maxY ?? 0
}

func loadSpriteFrames(spriteRoot: URL) -> [String: [NSImage]] {
    var spriteFrames: [String: [NSImage]] = [:]
    let animationFolders = [
        ("waiting", "waiting"),
        ("running", "running-v2"),
        ("review", "review"),
        ("pocket", "pocket"),
        ("waving", "waving"),
        ("pointing", "pointing")
    ]
    for (name, folderName) in animationFolders {
        let folder = spriteRoot.appendingPathComponent(folderName)
        let files = ((try? FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: nil)) ?? [])
            .filter { $0.pathExtension.lowercased() == "png" }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
        spriteFrames[name] = files.compactMap { NSImage(contentsOf: $0) }
    }
    return spriteFrames
}

final class OverlayView: NSView {
    let spriteRoot: URL
    let duration: TimeInterval
    let started = Date()
    var timer: Timer?
    var spriteFrames: [String: [NSImage]] = [:]

    init(frame: NSRect, spriteRoot: URL, duration: TimeInterval) {
        self.spriteRoot = spriteRoot
        self.duration = duration
        super.init(frame: frame)
        wantsLayer = true
        layer?.backgroundColor = NSColor.clear.cgColor
        loadAnimations()
        timer = Timer.scheduledTimer(withTimeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in
            guard let self else { return }
            self.needsDisplay = true
            if Date().timeIntervalSince(self.started) > self.duration + 0.5 {
                NSApp.terminate(nil)
            }
        }
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override var isOpaque: Bool { false }

    func loadAnimations() {
        spriteFrames = loadSpriteFrames(spriteRoot: spriteRoot)
    }

    override func draw(_ dirtyRect: NSRect) {
        NSColor.clear.setFill()
        dirtyRect.fill()

        let elapsed = Date().timeIntervalSince(started)
        let progress = min(elapsed / max(duration, 0.1), 1.0)
        drawBanner(progress: progress)
        drawSprite(elapsed: elapsed, progress: progress)

        if progress > 0.72 {
            drawGoodbye()
        }
    }

    func drawBanner(progress: Double) {
        let alpha = min(1.0, progress * 8.0)
        let rect = NSRect(x: bounds.width * 0.035, y: bounds.height - 155, width: min(bounds.width * 0.45, 560), height: 112)
        NSColor(calibratedRed: 0.86, green: 0.0, blue: 0.0, alpha: alpha).setFill()
        rect.fill()
        NSColor(calibratedWhite: 1.0, alpha: alpha).setStroke()
        let path = NSBezierPath(rect: rect)
        path.lineWidth = 5
        path.stroke()

        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.monospacedSystemFont(ofSize: 62, weight: .heavy),
            .foregroundColor: NSColor(calibratedWhite: 1.0, alpha: alpha)
        ]
        NSString(string: "RED CARD").draw(at: NSPoint(x: rect.minX + 30, y: rect.minY + 25), withAttributes: attrs)
    }

    func drawSprite(elapsed: TimeInterval, progress: Double) {
        let name: String
        let anchorX: CGFloat
        if progress < 0.42 {
            name = "running"
            anchorX = bounds.width * CGFloat(0.12 + 0.60 * (progress / 0.42))
        } else if progress < 0.76 {
            name = "review"
            anchorX = bounds.width * 0.84
        } else {
            name = "waving"
            anchorX = bounds.width * 0.84
        }

        guard let frames = spriteFrames[name], !frames.isEmpty else { return }
        let index = Int(elapsed * 8.0) % frames.count
        let image = frames[index]
        let scale: CGFloat = 1.65
        let size = NSSize(width: image.size.width * scale, height: image.size.height * scale)
        let origin = NSPoint(x: anchorX - size.width / 2, y: bounds.height * 0.12)
        image.draw(in: NSRect(origin: origin, size: size), from: .zero, operation: .sourceOver, fraction: 1.0)
    }

    func drawGoodbye() {
        let text = "JUST LEAVE THE CALL"
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 38, weight: .black),
            .foregroundColor: NSColor.white,
            .strokeColor: NSColor.black,
            .strokeWidth: -3
        ]
        let size = NSString(string: text).size(withAttributes: attrs)
        NSString(string: text).draw(
            at: NSPoint(x: (bounds.width - size.width) / 2, y: 42),
            withAttributes: attrs
        )
    }
}

final class CornerView: NSView {
    let spriteRoot: URL
    let duration: TimeInterval
    let started = Date()
    var timer: Timer?
    var spriteFrames: [String: [NSImage]] = [:]

    init(frame: NSRect, spriteRoot: URL, duration: TimeInterval) {
        self.spriteRoot = spriteRoot
        self.duration = duration
        super.init(frame: frame)
        wantsLayer = true
        layer?.backgroundColor = NSColor.clear.cgColor
        loadAnimations()
        timer = Timer.scheduledTimer(withTimeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in
            guard let self else { return }
            self.needsDisplay = true
            if Date().timeIntervalSince(self.started) > self.duration + 0.5 {
                NSApp.terminate(nil)
            }
        }
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override var isOpaque: Bool { false }

    func loadAnimations() {
        spriteFrames = loadSpriteFrames(spriteRoot: spriteRoot)
    }

    override func draw(_ dirtyRect: NSRect) {
        NSColor.clear.setFill()
        dirtyRect.fill()

        let elapsed = Date().timeIntervalSince(started)
        let progress = min(elapsed / max(duration, 0.1), 1.0)
        let name: String
        if progress < 0.42 {
            name = "running"
        } else if progress < 0.76 {
            name = "review"
        } else {
            name = "waving"
        }

        guard let frames = spriteFrames[name], !frames.isEmpty else { return }
        let image = frames[Int(elapsed * 8.0) % frames.count]
        let scale: CGFloat = 1.2
        let size = NSSize(width: image.size.width * scale, height: image.size.height * scale)
        let origin = NSPoint(x: (bounds.width - size.width) / 2, y: 8)
        image.draw(in: NSRect(origin: origin, size: size), from: .zero, operation: .sourceOver, fraction: 1.0)
    }
}

final class DemoView: NSView {
    let spriteRoot: URL
    let statePath: String
    let screenFrame: NSRect
    let topLeftReferenceY: CGFloat
    let parentPID: pid_t
    var timer: Timer?
    var spriteFrames: [String: [NSImage]] = [:]
    var lastModified: Date?
    var visible = false
    var xTopLeft: CGFloat = 40
    var yTopLeft: CGFloat = 520
    var animation = "waiting"
    var animationStarted = Date()
    var scale: CGFloat = 1.2
    var facing = "right"
    var goodbyeScreen: NSImage?
    let started = Date()

    init(frame: NSRect, spriteRoot: URL, statePath: String, screenFrame: NSRect, topLeftReferenceY: CGFloat, parentPID: pid_t) {
        self.spriteRoot = spriteRoot
        self.statePath = statePath
        self.screenFrame = screenFrame
        self.topLeftReferenceY = topLeftReferenceY
        self.parentPID = parentPID
        super.init(frame: frame)
        wantsLayer = true
        layer?.backgroundColor = NSColor.clear.cgColor
        spriteFrames = loadSpriteFrames(spriteRoot: spriteRoot)
        goodbyeScreen = NSImage(contentsOf: spriteRoot.appendingPathComponent("goodbye-screen.png"))
        timer = Timer.scheduledTimer(withTimeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in
            guard let self else { return }
            if !processIsRunning(self.parentPID) {
                NSApp.terminate(nil)
                return
            }
            self.readState()
            self.needsDisplay = true
        }
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override var isOpaque: Bool { false }

    func readState() {
        guard FileManager.default.fileExists(atPath: statePath) else {
            NSApp.terminate(nil)
            return
        }
        let url = URL(fileURLWithPath: statePath)
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: statePath),
              let modified = attrs[.modificationDate] as? Date else { return }
        if lastModified == modified { return }
        lastModified = modified
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
        visible = object["visible"] as? Bool ?? visible
        xTopLeft = CGFloat(object["x"] as? Double ?? Double(xTopLeft))
        yTopLeft = CGFloat(object["y"] as? Double ?? Double(yTopLeft))
        let newAnimation = object["animation"] as? String ?? animation
        if newAnimation != animation {
            animationStarted = Date()
        }
        animation = newAnimation
        scale = CGFloat(object["scale"] as? Double ?? Double(scale))
        facing = object["facing"] as? String ?? facing
        if object["quit"] as? Bool == true {
            NSApp.terminate(nil)
        }
    }

    override func draw(_ dirtyRect: NSRect) {
        NSColor.clear.setFill()
        dirtyRect.fill()
        guard visible else { return }
        let elapsed = Date().timeIntervalSince(animationStarted)
        if animation == "goodbye" {
            drawGoodbyeShade(elapsed: elapsed)
            return
        }
        let displayAnimation = animation
        let frameName = displayAnimation == "redcard" ? "pocket" : displayAnimation
        let fallbackName = spriteFrames[frameName]?.isEmpty == false ? frameName : "waving"
        guard let frames = spriteFrames[fallbackName], !frames.isEmpty else { return }
        let frameIndex = frameIndexFor(animation: displayAnimation, elapsed: elapsed, frameCount: frames.count)
        let image = frames[frameIndex]
        let size = NSSize(width: image.size.width * scale, height: image.size.height * scale)
        let cocoaY = topLeftReferenceY - yTopLeft - size.height
        let localX = xTopLeft - screenFrame.minX
        let localY = cocoaY - screenFrame.minY
        let rect = NSRect(x: localX, y: localY, width: size.width, height: size.height)
        let globalCenter = NSPoint(x: xTopLeft + size.width / 2, y: cocoaY + size.height / 2)
        if screenFrame.contains(globalCenter) {
            if facing == "left" {
                NSGraphicsContext.saveGraphicsState()
                let transform = NSAffineTransform()
                transform.translateX(by: rect.midX, yBy: rect.midY)
                transform.scaleX(by: -1.0, yBy: 1.0)
                transform.translateX(by: -rect.midX, yBy: -rect.midY)
                transform.concat()
                image.draw(in: rect, from: .zero, operation: .sourceOver, fraction: 1.0)
                NSGraphicsContext.restoreGraphicsState()
            } else {
                image.draw(in: rect, from: .zero, operation: .sourceOver, fraction: 1.0)
            }
        }
    }

    func drawGoodbyeShade(elapsed: TimeInterval) {
        let progress = min(1.0, elapsed / 1.15)
        let shadeHeight = bounds.height * progress
        let shadeRect = NSRect(x: 0, y: bounds.height - shadeHeight, width: bounds.width, height: shadeHeight)
        NSColor.black.setFill()
        shadeRect.fill()

        guard progress > 0.62 else { return }
        drawGoodbyeScreen()
    }

    func drawGoodbyeScreen() {
        guard let image = goodbyeScreen else { return }
        let imageRatio = image.size.width / max(image.size.height, 1)
        let boundsRatio = bounds.width / max(bounds.height, 1)
        let size: NSSize
        if imageRatio > boundsRatio {
            size = NSSize(width: bounds.width, height: bounds.width / imageRatio)
        } else {
            size = NSSize(width: bounds.height * imageRatio, height: bounds.height)
        }
        let rect = NSRect(
            x: (bounds.width - size.width) / 2,
            y: (bounds.height - size.height) / 2,
            width: size.width,
            height: size.height
        )
        image.draw(in: rect, from: .zero, operation: .sourceOver, fraction: 1.0)
    }

    func frameIndexFor(animation: String, elapsed: TimeInterval, frameCount: Int) -> Int {
        if animation == "running" {
            return Int(elapsed * 5.0) % frameCount
        }
        if animation == "waiting" {
            let fps = 2.5
            let holdFrameIndex = min(3, frameCount - 1)
            let holdStart = Double(holdFrameIndex) / fps
            let holdSeconds = 0.85
            let animationSeconds = Double(frameCount) / fps + holdSeconds
            let pauseSeconds = 2.2
            let cycleElapsed = elapsed.truncatingRemainder(dividingBy: animationSeconds + pauseSeconds)
            if cycleElapsed >= animationSeconds {
                return holdFrameIndex
            }
            if cycleElapsed >= holdStart && cycleElapsed < holdStart + holdSeconds {
                return holdFrameIndex
            }
            let adjustedElapsed = cycleElapsed > holdStart ? cycleElapsed - holdSeconds : cycleElapsed
            return min(Int(adjustedElapsed * fps), frameCount - 1)
        }

        let fps = animation == "redcard" ? 4.0 : 5.0
        if animation == "waving" {
            let holdFrameIndex = min(2, frameCount - 1)
            return min(Int(elapsed * fps), holdFrameIndex)
        }
        let pauseSeconds = 2.5
        let playbackFrameCount = frameCount
        let holdFrameIndex = frameCount - 1
        let animationSeconds = Double(playbackFrameCount) / fps
        let cycleSeconds = animationSeconds + pauseSeconds
        let cycleElapsed = elapsed.truncatingRemainder(dividingBy: cycleSeconds)
        if cycleElapsed >= animationSeconds {
            return holdFrameIndex
        }
        return min(Int(cycleElapsed * fps), playbackFrameCount - 1)
    }
}

let args = CommandLine.arguments
let spriteRoot = URL(fileURLWithPath: args.count > 1 ? args[1] : "assets/sprites")
let duration = args.count > 2 ? (Double(args[2]) ?? 6.0) : 6.0
NSApplication.shared.setActivationPolicy(.accessory)
var windows: [NSWindow] = []
var demoOverlayLock: Int32?
if args.count > 3 && args[3] == "screens" {
    let screens = overlayScreens()
    let topLeftReferenceY = overlayTopLeftReferenceY(screens: screens)
    print("topLeftReferenceY=\(Int(topLeftReferenceY))")
    for (index, screen) in screens.enumerated() {
        let frame = screen.frame
        let top = topLeftReferenceY - frame.maxY
        let bottom = topLeftReferenceY - frame.minY
        print(
            "screen \(index): cocoa=(\(Int(frame.minX)),\(Int(frame.minY)),\(Int(frame.maxX)),\(Int(frame.maxY))) " +
            "topLeft=(\(Int(frame.minX)),\(Int(top)),\(Int(frame.maxX)),\(Int(bottom))) " +
            "probe=(\(Int(frame.minX + 40)),\(Int(top + 520)))"
        )
    }
    exit(0)
}
if args.count > 7 && args[3] == "corner" {
    let x = Double(args[4]) ?? 40
    let yTop = Double(args[5]) ?? 520
    let width = Double(args[6]) ?? 260
    let height = Double(args[7]) ?? 260
    let screens = overlayScreens()
    let topLeftReferenceY = overlayTopLeftReferenceY(screens: screens)
    let cocoaY = topLeftReferenceY - yTop - height
    let frame = NSRect(x: x, y: cocoaY, width: width, height: height)
    let window = NSWindow(
        contentRect: frame,
        styleMask: [.borderless],
        backing: .buffered,
        defer: false
    )
    window.isOpaque = false
    window.backgroundColor = .clear
    window.ignoresMouseEvents = true
    window.level = .screenSaver
    window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
    window.contentView = CornerView(frame: NSRect(x: 0, y: 0, width: width, height: height), spriteRoot: spriteRoot, duration: duration)
    window.orderFrontRegardless()
    windows.append(window)
    NSApplication.shared.run()
    exit(0)
}
if args.count > 4 && args[3] == "demo" {
    let statePath = args[4]
    let parentPID = args.count > 5 ? pid_t(Int32(args[5]) ?? 0) : 0
    guard let lockDescriptor = acquireDemoOverlayLock() else {
        fputs("A Red Card referee overlay is already running.\n", stderr)
        exit(3)
    }
    demoOverlayLock = lockDescriptor
    let availableScreens = overlayScreens()
    var seenFrames: [NSRect] = []
    let screens = availableScreens.filter { screen in
        if seenFrames.contains(screen.frame) { return false }
        seenFrames.append(screen.frame)
        return true
    }
    let topLeftReferenceY = overlayTopLeftReferenceY(screens: screens)
    for screen in screens {
        let screenFrame = screen.frame
        let contentFrame = NSRect(x: 0, y: 0, width: screenFrame.width, height: screenFrame.height)
        let window = NSWindow(
            contentRect: screenFrame,
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )
        window.isOpaque = false
        window.backgroundColor = .clear
        window.ignoresMouseEvents = true
        window.level = .screenSaver
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
        window.contentView = DemoView(
            frame: contentFrame,
            spriteRoot: spriteRoot,
            statePath: statePath,
            screenFrame: screenFrame,
            topLeftReferenceY: topLeftReferenceY,
            parentPID: parentPID
        )
        window.orderFrontRegardless()
        windows.append(window)
    }
    NSApplication.shared.run()
    exit(0)
}
let screens = overlayScreens()

for screen in screens {
    let screenFrame = screen.frame
    let contentFrame = NSRect(x: 0, y: 0, width: screenFrame.width, height: screenFrame.height)
    let window = NSWindow(
        contentRect: screenFrame,
        styleMask: [.borderless],
        backing: .buffered,
        defer: false
    )
    window.isOpaque = false
    window.backgroundColor = .clear
    window.ignoresMouseEvents = true
    window.level = .screenSaver
    window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
    window.contentView = OverlayView(frame: contentFrame, spriteRoot: spriteRoot, duration: duration)
    window.orderFrontRegardless()
    windows.append(window)
}

NSApplication.shared.run()
