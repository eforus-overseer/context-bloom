# Host integrations

## Claude Code terminal

The skill works as `/context-bloom` when installed personally, or `/context-bloom:context-bloom` from the plugin. The status line is a separate optional installation, not automatically enabled by a skill or plugin manifest.

Merge a `statusLine` command into your existing `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 /absolute/path/to/skills/context-bloom/scripts/statusline.py",
    "padding": 1
  }
}
```

Quote paths containing spaces with your shell's quoting rules. The repo installer generates a correctly quoted command. Add `--ascii` for terminals without circle glyphs, or `--prepare 70 --compact 85` for different thresholds. The script reads the supplied `context_window.used_percentage`; its fallback sums current input, cache creation, and cache read tokens and divides by the host's context window size. Missing usage displays unknown, never zero. It performs no transcript reads or network requests.

It shows discrete growing circles in a terminal, not a floating graphical overlay. The HTML report provides a smooth resizing bubble. Terminal settings do not extend the Claude web UI.

## Codex

Invoke `$context-bloom`. In the CLI, use `/statusline` to enable the built-in context fields. The documented footer configuration lists supported items, not arbitrary shell-rendered widgets. This release supplies no injected Codex toolbar extension. Use the HTML report alongside the app for the graphical bubble; it is a snapshot with a labeled preview slider, not a live connection.

## Sources checked October 15, 2026

- [Claude status line](https://code.claude.com/docs/en/statusline)
- [Claude skills](https://code.claude.com/docs/en/skills)
- [Codex developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
- [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Codex skills](https://learn.chatgpt.com/docs/build-skills)

Packaging was inspired by [Ponytail](https://github.com/DietrichGebert/ponytail); this project has its own analysis, behavior and code.
