bl_info = {
    "name": "Node_To_Json",
    "Author": "Demingo Hill (Noizirom) (C)",
    "version": (0,1,0),
    "blender": (5, 2, 0),
    "location": "Node Editor > Sidebar > Node To Json",
    "description": "Save Node Groups to JSON and load Node Groups from JSON.",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "category": "Node Editor",
}

import bpy
import sys
import importlib
from bpy.utils import script_path_user
from pathlib import Path
from .pip_utils import pip_install_wheel_from, pip_uninstall


main_directory = Path(script_path_user()).joinpath("addons").joinpath(__package__).resolve()
wheels_path = main_directory.joinpath("Wheels")


def install_package(module_name):
    # Helper function to ensure that wheel is installed from Wheels folder
    try:
        __import__(module_name)
    except ImportError:
        pip_install_wheel_from(module_name, wheels_path)

        import site
        user_site = site.getusersitepackages()
        if user_site not in sys.path:
            sys.path.append(user_site)
        
        importlib.reload(sys.modules[module_name])


def delayed_setup():
    # Add anything that can't run until after the addon is set up
    # Start Node Group listener
    bpy.ops.scene.detect_new_node_group()
    print("Setup Complete!")
    return None


def register():
    # Pip install node_to_json before registering modules that import it
    try:
        install_package("node_to_json")
    except Exception as e:
        print(e)
        pass
    # Register all modules. If a RuntimeError occurs, uninstall node_to_json
    try:
        from .node_group_panel import register as _reg
        _reg()
    except RuntimeError as e:
        print(e)
        pip_uninstall("node_to_json")
        pass
    # Necessary to invoke listener after addon is set up
    bpy.app.timers.register(delayed_setup)



def unregister():
    # Uninstall node_to_json
    pip_uninstall("node_to_json")
    # Unregister all modules 
    from .node_group_panel import unregister as _unreg
    _unreg()


if __name__ == "__main__":
    register()


