# Plugins

External Python packages may register `EngineAdapter` implementations through the `cinenode.engines` entry-point group. Filesystem plugins are loaded only from `CINENODE_HOME/plugins`, only when explicitly allowlisted, and must return a `Plugin` contract. Registries are per application instance and reject duplicate IDs.
