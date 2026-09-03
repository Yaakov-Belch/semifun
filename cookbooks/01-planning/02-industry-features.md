# Industry Features

1. **Registration** — how providers get into the container. Annotations/decorators (`@Injectable`, `@Component`), explicit bindings (`bind(Interface).to(Impl)`), convention scanning, or configuration files.

2. **Resolution** — given a type/key, find and invoke the right provider. Includes auto-wiring (inspecting constructor signatures to resolve dependencies recursively).

3. **Scopes / lifetimes** — singleton (one per app), scoped (one per request/session), transient (new every time). Controls sharing and teardown.

4. **Hierarchical containers / child injectors** — a child scope inherits from a parent, can override bindings locally. Angular's component tree, Spring's parent-child contexts.

5. **Lifecycle hooks / cleanup** — `@PostConstruct`, `@PreDestroy`, `IDisposable`, generator-based teardown. The container manages not just creation but destruction.

6. **Lazy loading / lazy resolution** — don't instantiate until first use. Important for startup performance and optional dependencies.

7. **Parametric / named / qualified bindings** — when you have multiple implementations of the same type. `@Named("primary")` in Guice, `@Qualifier` in Spring, keyed services in .NET 8.
