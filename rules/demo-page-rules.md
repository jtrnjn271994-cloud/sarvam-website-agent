# Demo page rules

Draft, 13 Nov 2026. These rules apply to the test page built from an approved change.

## Rules

1. The demo page is a separate Vercel project. It is not part of the Sarvam site.
2. Deploy only after the user approves. The agent never deploys alone.
3. Show this banner on every screen: "Research prototype. Not an official Sarvam page."
4. Do not copy the logo. Write the name "Sarvam AI" in plain type.
5. Add a `noindex` meta tag. Send an `X-Robots-Tag` header with `noindex`.
6. Add no form that collects personal data.
7. Add no real payment and no real login.
8. Use simulated visitors only. Label every result SYNTHETIC.
9. Never deploy to a Sarvam server or a Sarvam domain.

## Code check list

A code check can confirm rules 3, 5, 6, 7 and 9 on the built files. A person confirms rules 2 and 4.

## Related

- [Brand rules](brand-rules.md)
- [Test scope rules](test-scope-rules.md)
