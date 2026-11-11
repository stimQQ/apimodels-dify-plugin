from dify_plugin import DifyPluginEnv, Plugin

# Video jobs can take several minutes; the tools wait up to 9 minutes before handing back a task ID.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=600))

if __name__ == "__main__":
    plugin.run()
