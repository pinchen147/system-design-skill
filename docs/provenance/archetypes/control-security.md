# Provenance — Control and security archetypes

Sources for the runtime pack. Return to the [archetype provenance index](../ARCHETYPES.md).

## Rate limiting and abuse control

| Claim | Source |
|---|---|
| Per-endpoint fail-open versus fail-closed rather than a blanket stance | https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/other_features/global_rate_limiting |
| 429 with `Retry-After` | https://www.rfc-editor.org/rfc/rfc6585#section-4 · https://www.rfc-editor.org/rfc/rfc9110#section-10.2.3 |
| In-DC round trip ~500 µs, so a 1 ms budget cannot contain a central call | https://sre.google/sre-book/addressing-cascading-failures/ |
| A fixed window can admit twice its nominal count across one boundary | derived from one full window immediately before and one immediately after the boundary. |
| Token- and leaky-bucket meters expose rate and burst/smoothing parameters | https://www.rfc-editor.org/rfc/rfc3290.html#section-5.1 |
| Sliding-counter production error around 0.003% | https://blog.cloudflare.com/counting-things-a-lot-of-different-things/ |
| 10 replicas × 100-token leases permits at most 1,000 tokens not yet visible to the broker; overshoot percentage is 1,000 ÷ the quota for the same window | derived; request rate alone does not determine the percentage. |
| ~1k req/s per subject | Design-envelope anti-gate, not a universal datastore threshold; measure the existing counter path. |

## Versioned control plane with cached data plane

| Claim | Source |
|---|---|
| Bootstrap from a snapshot, then follow a revision cursor; the stream is a hint, the poll is the repair | https://etcd.io/docs/v3.6/learning/api/#watch-api |
| One request capped near 1.5 MiB; keyspace 2 GiB by default | https://etcd.io/docs/v3.6/dev-guide/limit/ |
| Authorization tuples need a consistency token, not a cached bundle — the `Not when` boundary | https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/ |
| 50k × 100 KB ÷ 30 s = 167 MB/s and 1,667 req/s | derived |

## Identity, session, and revocation

| Claim | Source |
|---|---|
| Reauthentication bounds: 24 h absolute with 1 h inactivity at ordinary assurance; 12 h with 15 min at the highest | https://pages.nist.gov/800-63-4/sp800-63b.html |
| Refresh tokens sender-constrained or rotated, preserving the family so reuse reveals compromise | https://www.rfc-editor.org/rfc/rfc9700.html |
| Exact redirect matching, one-time codes, transaction-bound nonces | https://www.rfc-editor.org/rfc/rfc9700.html · https://openid.net/specs/openid-connect-core-1_0.html |
| Proof-of-possession binding | https://www.rfc-editor.org/rfc/rfc9449.html · https://www.rfc-editor.org/rfc/rfc8705.html |
| 10M ÷ 300 s = 33,333/s; 10M ÷ 30 s = 333,333/s | derived |

## Secret and key hierarchy

| Claim | Source |
|---|---|
| Wrapping-key usage period a day to a week when wrapping very large numbers of keys, up to two years for few; decrypt window up to three years beyond | https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf §5.3.6 |
| A key with random 96-bit nonces retires before 2^32 encryptions | https://csrc.nist.gov/pubs/sp/800/38/d/final §8.3 |
| Envelope encryption: rotation rewrites key material, not payloads | https://developer.hashicorp.com/vault/docs/internals/architecture |
| 2^32 ÷ 10,000/s = 429,497 s = 4.97 days | derived |
