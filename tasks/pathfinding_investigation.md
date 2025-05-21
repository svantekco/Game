# Pathfinding Investigation

This document tracks tasks related to the resource search bug.

## Background

Villagers sometimes fail to locate resources even when they are close by. The log shows messages such as:

```
find_nearest_resource failed cluster search around (x, y) for TREE
```

when trees or rocks exist only a few tiles away. The fallback BFS search may also hit the search limit of 50,000 nodes which is far too large for such a short distance.

## Proposed Tasks

1. **Reproduce the bug**
   - [ ] Add a unit test that creates a minimal map with a resource 10 tiles from the origin.
   - [ ] Ensure that `find_nearest_resource` returns that position within a small search limit.

2. **Improve logging**
   - [ ] Emit debug logs when clusters are computed and when cached clusters are used.
   - [ ] Log the number of clusters checked and the path length for each candidate.

3. **Investigate cluster caching**
   - [ ] Verify that the cluster cache updates when resources are depleted.
   - [ ] Check if the cache key granularity causes stale results.

4. **Fix search failure**
   - [ ] Adjust `find_nearest_resource` to fall back sooner when clusters are empty.
   - [ ] Consider disabling caching or reducing the radius when close to the target.
   - [ ] Validate the fix with the new unit test.
