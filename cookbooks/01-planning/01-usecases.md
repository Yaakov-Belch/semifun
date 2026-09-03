# Use Cases

1. **Swapping implementations** — production DB vs. test mock, real email sender vs. fake. The canonical motivation: code against an interface, wire the concrete at composition time.

2. **Managing resource lifetimes** — a DB connection pool lives for the app, a DB session lives for one request, a transaction lives for one operation. The framework creates, shares, and tears down at the right moment.

3. **Cross-cutting concerns without coupling** — logging, auth, metrics, tracing. Functions that need a logger shouldn't know how logging is configured. Functions that need the current user shouldn't import the auth module.

4. **Plugin/extension architecture** — third-party code registers implementations that the core discovers and calls. The core doesn't import the plugins; the plugins don't import each other.

5. **Configuration propagation** — settings, feature flags, environment-specific values flow to wherever they're needed without threading them through every call signature.
