# Provenance — Data delivery archetypes

Sources for the runtime pack. Return to the [archetype provenance index](../ARCHETYPES.md).

## Media pipeline and edge delivery

| Claim | Source |
|---|---|
| Multipart parts can carry checksums, and completion must identify the uploaded parts | https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html |
| HLS uses playlists and media segments for adaptive streaming | https://www.rfc-editor.org/rfc/rfc8216.html#section-3 |
| MPEG-DASH represents alternative media encodings as segmented representations | https://standards.iso.org/ittf/PubliclyAvailableStandards/c083314_ISO_IEC_23009-1_2022(en).zip |
| CDN caching and origin offload compose the cache rules already sourced for the cache archetype | [Derived serving — Global edge and hierarchical cache](derived-serving.md#global-edge-and-hierarchical-cache) |
| 5M DAU × 30 MB new media/user/day = 150 TB/day | derived illustrative envelope; CDN dollars require the selected provider's contracted regional rate and measured delivered bytes. |

## Immutable artifact distribution

| Claim | Source |
|---|---|
| 72-hour withdrawal window; past it, no dependents, under 300 weekly downloads, single owner; a used version identifier can never be reused | https://docs.npmjs.com/policies/unpublish |
| A version identifies an immutable snapshot, authenticated by a checksum database | https://go.dev/ref/mod |
| Role separation, threshold signatures, expiring freshness metadata defeating replay | https://theupdateframework.github.io/specification/latest/ |
| Provenance attestation and hermetic build levels | https://slsa.dev/spec/ |
| Digest as the artifact's name; unchanged layers are not re-transferred | https://github.com/opencontainers/image-spec/blob/main/descriptor.md |

**Rejected.** "Freshness metadata expires daily." The specification mandates expiration checking but
prescribes no interval; the daily figure is an implementation convention.
