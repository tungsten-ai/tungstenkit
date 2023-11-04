import click

from tungstenkit._internal.model_def_loader import create_model_def_loader


@click.command()
@click.option("--model-module", "-m", help="Tungsten model module")
@click.option("--class-name", "-c", help="Class name in Tungsten model module")
def post_model_build(model_module, class_name):
    model_def_loader = create_model_def_loader(model_module, class_name, lazy_import=False)
    model_def_loader.model_class.post_build()


if __name__ == "__main__":
    post_model_build()
