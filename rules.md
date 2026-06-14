# Code Quality Rules

1. **Name things like you'll read them at 2 AM** - variables, functions, and classes must reveal intent, not abbreviate it.

2. **One function, one job** - if you need "and" to describe what it does, split it.

3. **No magic numbers or strings** - every meaningful literal gets a named constant.

4. **Handle errors explicitly, not optimistically** - catch specific exceptions, surface meaningful messages, never swallow failures silently.

5. **Avoid side effects in functions** - a function should return a value, not secretly mutate state elsewhere.

6. **Use types everywhere you can** - annotate function signatures, return types, and data models without exception.

7. **Comments explain why, not what** - if the comment restates the code, delete it.

8. **Keep functions short and flat** - max ~30 lines, max 2 levels of nesting; use early returns to kill nested ifs.

9. **Validate inputs at every boundary** - never trust data coming from outside your function, API, or module.

10. **Don't repeat yourself, but don't over-abstract either** - duplicate twice is fine, three times means extract; abstract on the third recurrence, not the first.
