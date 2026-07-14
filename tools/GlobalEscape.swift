import ApplicationServices
import Foundation

var targetPid: pid_t = 0
var checkOnly = false

func requestInputMonitoringAccess() -> Bool {
    if CGPreflightListenEventAccess() {
        return true
    }
    return CGRequestListenEventAccess()
}

func callback(
    proxy: CGEventTapProxy,
    type: CGEventType,
    event: CGEvent,
    refcon: UnsafeMutableRawPointer?
) -> Unmanaged<CGEvent>? {
    if type == .keyDown {
        let keyCode = event.getIntegerValueField(.keyboardEventKeycode)
        if keyCode == 53 {
            kill(targetPid, SIGINT)
            DispatchQueue.main.async {
                CFRunLoopStop(CFRunLoopGetMain())
            }
        }
    }
    return Unmanaged.passUnretained(event)
}

guard CommandLine.arguments.count == 2 else {
    fputs("usage: redcard-global-escape <pid|--check>\n", stderr)
    exit(2)
}

if CommandLine.arguments[1] == "--check" {
    checkOnly = true
} else if let pid = Int32(CommandLine.arguments[1]) {
    targetPid = pid_t(pid)
} else {
    fputs("usage: redcard-global-escape <pid|--check>\n", stderr)
    exit(2)
}

guard requestInputMonitoringAccess() else {
    fputs(
        "Red Card requested Input Monitoring access from macOS, but access is not granted yet. Respond to the macOS prompt, then quit and reopen ChatGPT.\n",
        stderr
    )
    exit(1)
}

let mask = CGEventMask(1 << CGEventType.keyDown.rawValue)
guard let tap = CGEvent.tapCreate(
    tap: .cgSessionEventTap,
    place: .headInsertEventTap,
    options: .listenOnly,
    eventsOfInterest: mask,
    callback: callback,
    userInfo: nil
) else {
    fputs("Red Card received Input Monitoring access, but the global Escape event tap could not start.\n", stderr)
    exit(1)
}

let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
CFRunLoopAddSource(CFRunLoopGetCurrent(), source, .commonModes)
CGEvent.tapEnable(tap: tap, enable: true)
if checkOnly {
    exit(0)
}
CFRunLoopRun()
