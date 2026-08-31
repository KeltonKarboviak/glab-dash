Type: task
Status: complete

## Task

Add a `?` keybinding that shows Textual's built-in help/keys panel, listing
all active bindings (including the ones currently marked `show=False` in
`GlabDashApp.BINDINGS`, since the panel lists everything regardless of
`show`).

Textual's `App` already ships `action_show_help_panel` /
`action_hide_help_panel` (mounts/removes a `HelpPanel` widget) but no toggle
action, so add a `action_toggle_help_panel` on `GlabDashApp` and bind `?` to
it.

## Definition of done

- Pressing `?` mounts the `HelpPanel`; pressing `?` again dismisses it.
- Test covering the toggle via `pilot.press("?")`.
