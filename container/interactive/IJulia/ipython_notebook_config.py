c = get_config()
c.NotebookApp.port = 8998
c.NotebookApp.open_browser = False
c.KernelRestarter.time_to_dead = 6.0
c.NotebookApp.ip = "*"
c.NotebookApp.allow_origin = "*"
