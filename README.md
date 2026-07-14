<!--
Codex bootstrap: If the user asks to build Red Card, clone or open this
repository first, read AGENTS.md, and follow its guide before anything else.
-->

# Red Card

<p align="center">
<img
  src="assets/readme-header.png"
  alt="Red Card in use during a video call"
  width="100%"
/>
</p>

Red Card is a webcam-powered Codex skill that ejects you from work, and you can
build it yourself.

Hold up a red card and the app sends your goodbye, leaves the call, blocks time
on your calendar, turns on your vacation responder, and runs a tiny referee
animation. You do not need to know how to code—Codex walks you through setup
and helps you make it your own.

## What You'll Need

- A Mac with ChatGPT for macOS and Codex access
- Google Chrome, signed into the account you want Red Card to use
- Python 3.11 or newer and the Xcode Command Line Tools
- Your Mac's camera, or a connected webcam
- A physical red card, or a phone showing the screen below

Open [this image](https://raw.githubusercontent.com/openai/redcard/main/assets/red-card.png)
full-screen on your phone—or print it—and hold it up to the webcam.

## How To Use

### Codex Take the Wheel

Open ChatGPT on macOS in Codex mode and type:

```text
Help me build the project at https://github.com/openai/redcard
```

<p align="center">
<img
  src="assets/codex-setup.png"
  alt="Starting the Red Card setup from Codex"
  width="100%"
/>
</p>

Codex will install a self-contained `$redcard` skill, build its native helpers,
and run the required permission and camera checks. Setup stops before the real
Red Card sequence starts. If Codex asks you to reload or start a fresh task
after setup, do that once so the newly installed skill becomes available.

Once setup is finished:

1. Join a Meet call in Chrome.
2. Type `$redcard` in Codex.
3. Hold up your red card when you are ready to leave.

Red Card takes it from there. Press **Esc** at any time to stop Red Card, even
while Chrome is focused.

## Permissions

The setup installer checks permissions before the first real `$redcard` run.
When macOS asks, click **Allow**. If a setting needs to be changed manually,
Codex will take you to:

- **System Settings > Privacy & Security > Camera**
- **System Settings > Privacy & Security > Accessibility**
- **System Settings > Privacy & Security > Input Monitoring**, if macOS asks
  for it so the global Esc shortcut can work

Enable **ChatGPT** for these permissions. You may need to quit and reopen
ChatGPT after changing a permission.

In Chrome, also enable **View > Developer > Allow JavaScript from Apple
Events**. Setup and every real Red Card launch verify this setting.

## Remix It

Ask Codex to change the goodbye message, calendar block, vacation response,
sleep behavior, red-card sensitivity, or referee animation. Describe what you
want in plain language and Codex will update and test it with you.

<p align="center">
  <img src="assets/footer.png" alt="Red Card referee animation sequence" width="100%" />
</p>
