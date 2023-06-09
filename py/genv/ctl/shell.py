import argparse

import genv.sdk


def do_init() -> None:
    """Prints the init shell script"""

    print(
        """\
_genv_append_to_env()
{
  # based on https://unix.stackexchange.com/a/415028
  export $1="${!1:+${!1}:}$2"
}

_genv_backup_env()
{
  if [ -n "${!1}" ]; then
    export GENV_BACKUP_ENV_$1="${!1}"
    _genv_append_to_env GENV_BACKUP_ENVS $1
  fi
}

_genv_set_env()
{
  export $1="$2"
  _genv_append_to_env GENV_ENVS $1
}

_genv_replace_env()
{
  _genv_backup_env $1
  _genv_set_env $1 "$2"
}

_genv_unset_env()
{
  unset $1
  # TODO(raz): remove from 'GENV_ENVS'
}

_genv_unset_envs()
{
  IFS=: read -a names <<< "$GENV_ENVS"
  unset GENV_ENVS

  for name in "${names[@]}"
  do
    unset $name
  done
}

_genv_restore_env()
{
  backup="GENV_BACKUP_ENV_$1"
  if [ -n "${!backup}" ]; then
    export $1="${!backup}"
  fi
  unset $backup
}

_genv_restore_envs()
{
  IFS=: read -a names <<< "$GENV_BACKUP_ENVS"
  unset GENV_BACKUP_ENVS

  for name in "${names[@]}"
  do
    _genv_restore_env $name
  done
}

genvctl()
{
  local command="${1:-}"
  if [ "$#" -gt 0 ]; then
    shift
  fi

  case "$command" in
  activate|deactivate)
    eval "$(command genvctl $command --shell $$ $@)"
    ;;
  config)
    command genvctl config $@

    if [ "$?" -eq 0 ]; then
      eval "$(command genvctl shell --reconfigure)"
    fi
    ;;
  attach)
    command genvctl $command $@

    if [ "$?" -eq 0 ]; then
      eval "$(command genvctl shell --reattach)"
    fi
    ;;
  shell)
    if [ "$#" -eq 0 ]; then
      command genvctl shell --ok
    else
      command genvctl shell $@
    fi
    ;;
  *)
    command genvctl $command $@
    ;;
  esac
}
"""
    )


def error_msg() -> str:
    """Returns an error message"""

    return """\
Your shell is not properly initialized at the moment.
Run the following command to initialize it.
You should also add it to your ~/.bashrc or any equivalent file.

    eval "$(genvctl shell --init)"
"""


def do_error() -> None:
    """Prints an error message"""

    print(error_msg())


def do_ok() -> None:
    """Prints an ok message"""

    print(
        """\
Your shell is initialized properly and you are all set.
Run the following command to check the status of your environment:

    genvctl status

If you are not sure how to continue from here, check out the quick start tutorial at https://docs.genv.dev/overview/quickstart.html.
"""
    )


def do_reattach() -> None:
    """Refreshes the shell indices environment variables"""

    indices = genv.sdk.refresh_attached()

    print(
        f"""\
_genv_replace_env CUDA_VISIBLE_DEVICES {",".join(map(str, indices)) if indices else "-1"}
"""
    )


def do_reconfigure() -> None:
    """Refreshes the shell configuration environment variables"""

    config = genv.sdk.refresh_configuration()

    for name, value in [
        ("GENV_ENVIRONMENT_NAME", config.name),
        ("GENV_GPU_MEMORY", config.gpu_memory),
        ("GENV_GPUS", config.gpus),
    ]:
        if value is not None:
            print(f"_genv_set_env {name} {value}")
        else:
            print(f"_genv_unset_env {name}")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Adds "genvctl shell" arguments to a parser.
    """

    parser.add_argument(
        "--init",
        action="store_const",
        dest="action",
        const="init",
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "--ok",
        action="store_const",
        dest="action",
        const="ok",
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "--reattach",
        action="store_const",
        dest="action",
        const="reattach",
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "--reconfigure",
        action="store_const",
        dest="action",
        const="reconfigure",
        help=argparse.SUPPRESS,
    )


def run(args: argparse.Namespace) -> None:
    """
    Runs the "genvctl shell" logic.
    """

    if args.action == "init":
        do_init()
    elif args.action == "ok":
        do_ok()
    elif args.action == "reattach":
        do_reattach()
    elif args.action == "reconfigure":
        do_reconfigure()
    else:
        do_error()
