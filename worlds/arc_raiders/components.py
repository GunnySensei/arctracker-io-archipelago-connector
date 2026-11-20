from worlds.LauncherComponents import Component, Type, components, launch


def run_client(*args: str) -> None:
    from .client.launch import launch_arc_client
    launch(launch_arc_client, name="ARC Raiders Client", args=args)


components.append(Component("ARC Raiders Client", func=run_client, game_name="ARC Raiders",
                            component_type=Type.CLIENT, supports_uri=True))


def run_hud(*args: str) -> None:
    from .client.hud import run
    launch(run, name="ARC Raiders HUD", args=args or ("http://127.0.0.1:38300",))


components.append(Component("ARC Raiders HUD", func=run_hud, component_type=Type.CLIENT))
