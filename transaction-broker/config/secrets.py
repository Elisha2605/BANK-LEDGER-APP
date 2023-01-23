from dotenv import dotenv_values
from utility.result import Err, Ok
import sys
import os

_envs = dotenv_values("../.env")
print(_envs.__dict__)

_secrets = {
    "RELOAD_UVICORN": _envs.get("RELOAD_UVICORN") or os.environ.get("RELOAD_UVICORN"),
    "BROKER_PORT": _envs.get("BROKER_PORT") or os.environ.get("BROKER_PORT"),
    "BROKER_HOST": _envs.get("BROKER_HOST") or os.environ.get("BROKER_HOST"),
}


def get_env(env: str) -> str:
    if _secrets[env] is not None:
        return _secrets[env]  # type: ignore | can only be str
    else:
        print(f"ENV '{env}' does not exist.\nExiting...")
        sys.exit(1)


def validate_envs() -> Err[str] | Ok[str]:
    for key, value in _secrets.items():
        if value is None:
            return Err("UnsetEnvError", f"The ENV '{key} is not set.")

    return Ok("All ENVs set correctly")
