import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Type
from urllib import request
from urllib.parse import urlparse

import jinja2
import jwt
import shortuuid
from fastapi.routing import APIRoute
from packaging import version
from pydantic.schema import field_schema

from lnbits_internal.jinja2_templating import Jinja2Templates
from lnbits_internal.nodes import get_node_class
from lnbits_internal.requestvars import g
from lnbits_internal.settings import settings
from lnbits_internal.utils.crypto import AESCipher

from .db import FilterModel


def get_db_vendor_name():
    db_url = settings.lnbits_database_url
    return (
        "PostgreSQL"
        if db_url and db_url.startswith("postgres://")
        else (
            "CockroachDB"
            if db_url and db_url.startswith("cockroachdb://")
            else "SQLite"
        )
    )


def urlsafe_short_hash() -> str:
    return shortuuid.uuid()


def url_for(endpoint: str, external: Optional[bool] = False, **params: Any) -> str:
    base = g().base_url if external else ""
    url_params = "?"
    for key, value in params.items():
        url_params += f"{key}={value}&"
    url = f"{base}{endpoint}{url_params}"
    return url


def static_url_for(static: str, path: str) -> str:
    return f"/{static}/{path}?v={settings.server_startup_time}"


def template_renderer(additional_folders: Optional[list] = None) -> Jinja2Templates:
    folders = ["lnbits/templates", "lnbits/core/templates"]
    if additional_folders:
        additional_folders += [
            Path(settings.lnbits_extensions_path, "extensions", f)
            for f in additional_folders
        ]
        folders.extend(additional_folders)
    t = Jinja2Templates(loader=jinja2.FileSystemLoader(folders))
    t.env.globals["static_url_for"] = static_url_for

    if settings.lnbits_ad_space_enabled:
        t.env.globals["AD_SPACE"] = settings.lnbits_ad_space.split(",")
        t.env.globals["AD_SPACE_TITLE"] = settings.lnbits_ad_space_title

    t.env.globals["VOIDWALLET"] = settings.lnbits_backend_wallet_class == "VoidWallet"
    t.env.globals["HIDE_API"] = settings.lnbits_hide_api
    t.env.globals["SITE_TITLE"] = settings.lnbits_site_title
    t.env.globals["LNBITS_DENOMINATION"] = (
        settings.lnbits_denomination
        if settings.lnbits_backend_wallet_class == "FakeWallet"
        else "sats"
    )
    t.env.globals["SITE_TAGLINE"] = settings.lnbits_site_tagline
    t.env.globals["SITE_DESCRIPTION"] = settings.lnbits_site_description
    t.env.globals["LNBITS_SHOW_HOME_PAGE_ELEMENTS"] = (
        settings.lnbits_show_home_page_elements
    )
    t.env.globals["LNBITS_CUSTOM_IMAGE"] = settings.lnbits_custom_image
    t.env.globals["LNBITS_CUSTOM_BADGE"] = settings.lnbits_custom_badge
    t.env.globals["LNBITS_CUSTOM_BADGE_COLOR"] = settings.lnbits_custom_badge_color
    t.env.globals["LNBITS_THEME_OPTIONS"] = settings.lnbits_theme_options
    t.env.globals["LNBITS_QR_LOGO"] = settings.lnbits_qr_logo
    t.env.globals["LNBITS_VERSION"] = settings.version
    t.env.globals["LNBITS_NEW_ACCOUNTS_ALLOWED"] = settings.new_accounts_allowed
    t.env.globals["LNBITS_AUTH_METHODS"] = settings.auth_allowed_methods
    t.env.globals["LNBITS_ADMIN_UI"] = settings.lnbits_admin_ui
    t.env.globals["LNBITS_EXTENSIONS_DEACTIVATE_ALL"] = (
        settings.lnbits_extensions_deactivate_all
    )
    t.env.globals["LNBITS_AUDIT_ENABLED"] = settings.lnbits_audit_enabled

    t.env.globals["LNBITS_SERVICE_FEE"] = settings.lnbits_service_fee
    t.env.globals["LNBITS_SERVICE_FEE_MAX"] = settings.lnbits_service_fee_max
    t.env.globals["LNBITS_SERVICE_FEE_WALLET"] = settings.lnbits_service_fee_wallet
    t.env.globals["LNBITS_NODE_UI"] = (
        settings.lnbits_node_ui and get_node_class() is not None
    )
    t.env.globals["LNBITS_NODE_UI_AVAILABLE"] = get_node_class() is not None
    t.env.globals["EXTENSIONS"] = list(settings.lnbits_installed_extensions_ids)

    if settings.lnbits_custom_logo:
        t.env.globals["USE_CUSTOM_LOGO"] = settings.lnbits_custom_logo

    if settings.lnbits_default_reaction:
        t.env.globals["USE_DEFAULT_REACTION"] = settings.lnbits_default_reaction

    if settings.lnbits_default_theme:
        t.env.globals["USE_DEFAULT_THEME"] = settings.lnbits_default_theme

    if settings.lnbits_default_border:
        t.env.globals["USE_DEFAULT_BORDER"] = settings.lnbits_default_border

    if settings.lnbits_default_gradient:
        t.env.globals["USE_DEFAULT_GRADIENT"] = settings.lnbits_default_gradient

    if settings.lnbits_default_bgimage:
        t.env.globals["USE_DEFAULT_BGIMAGE"] = settings.lnbits_default_bgimage

    if settings.bundle_assets:
        t.env.globals["INCLUDED_JS"] = ["bundle.min.js"]
        t.env.globals["INCLUDED_CSS"] = ["bundle.min.css"]
        t.env.globals["INCLUDED_COMPONENTS"] = ["bundle-components.min.js"]
    else:
        vendor_filepath = Path(settings.lnbits_path, "static", "vendor.json")
        with open(vendor_filepath) as vendor_file:
            vendor_files = json.loads(vendor_file.read())
            t.env.globals["INCLUDED_JS"] = vendor_files["js"]
            t.env.globals["INCLUDED_CSS"] = vendor_files["css"]
            t.env.globals["INCLUDED_COMPONENTS"] = vendor_files["components"]

    t.env.globals["WEBPUSH_PUBKEY"] = settings.lnbits_webpush_pubkey

    return t


def get_current_extension_name() -> str:
    """
    DEPRECATED: Use the repo name instead, will be removed in the future
    before: `register_invoice_listener(invoice_queue, get_current_extension_name())`
    after: `register_invoice_listener(invoice_queue, "my-extension")`

    Returns the name of the extension that calls this method.
    """
    import inspect
    import json
    import os

    callee_filepath = inspect.stack()[1].filename
    callee_dirname, _ = os.path.split(callee_filepath)

    path = os.path.normpath(callee_dirname)
    extension_director_name = path.split(os.sep)[-1]
    try:
        config_path = os.path.join(callee_dirname, "config.json")
        with open(config_path) as json_file:
            config = json.load(json_file)
        ext_name = config["name"]
    except Exception:
        ext_name = extension_director_name
    return ext_name


def generate_filter_params_openapi(model: Type[FilterModel], keep_optional=False):
    """
    Generate openapi documentation for Filters. This is intended to be used along
    parse_filters (see example)
    :param model: Filter model
    :param keep_optional: If false, all parameters will be optional,
    otherwise inferred from model
    """
    fields = list(model.__fields__.values())
    params = []
    for field in fields:
        schema, _, _ = field_schema(field, model_name_map={})

        description = "Supports Filtering"
        if (
            hasattr(model, "__search_fields__")
            and field.name in model.__search_fields__
        ):
            description += ". Supports Search"

        parameter = {
            "name": field.alias,
            "in": "query",
            "required": field.required if keep_optional else False,
            "schema": schema,
            "description": description,
        }
        params.append(parameter)

    return {
        "parameters": params,
    }


def is_valid_email_address(email: str) -> bool:
    email_regex = r"[A-Za-z0-9\._%+-]+@[A-Za-z0-9\.-]+\.[A-Za-z]{2,63}"
    return re.fullmatch(email_regex, email) is not None


def is_valid_username(username: str) -> bool:
    username_regex = r"(?=[a-zA-Z0-9._]{2,20}$)(?!.*[_.]{2})[^_.].*[^_.]"
    return re.fullmatch(username_regex, username) is not None


def is_valid_pubkey(pubkey: str) -> bool:
    if len(pubkey) != 64:
        return False
    try:
        int(pubkey, 16)
        return True
    except Exception as _:
        return False


def create_access_token(data: dict, token_expire_minutes: Optional[int] = None) -> str:
    minutes = token_expire_minutes or settings.auth_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode = {k: v for k, v in data.items() if v is not None}
    to_encode.update({"exp": expire})  # todo:check expiration
    return jwt.encode(to_encode, settings.auth_secret_key, "HS256")


def encrypt_internal_message(
    m: Optional[str] = None, urlsafe: bool = False
) -> Optional[str]:
    """
    Encrypt message with the internal secret key

    Args:
        m: Message to encrypt
        urlsafe: Whether to use URL-safe base64 encoding
    """
    if not m:
        return None
    return AESCipher(key=settings.auth_secret_key).encrypt(m.encode(), urlsafe=urlsafe)


def decrypt_internal_message(
    m: Optional[str] = None, urlsafe: bool = False
) -> Optional[str]:
    """
    Decrypt message with the internal secret key

    Args:
        m: Message to decrypt
        urlsafe: Whether the message uses URL-safe base64 encoding
    """
    if not m:
        return None
    return AESCipher(key=settings.auth_secret_key).decrypt(m, urlsafe=urlsafe)


def filter_dict_keys(data: dict, filter_keys: Optional[list[str]]) -> dict:
    if not filter_keys:
        # return shallow clone of the dict even if there are no filters
        return {**data}
    return {key: data[key] for key in filter_keys if key in data}


def version_parse(v: str):
    """
    Wrapper for version.parse() that does not throw if the version is invalid.
    Instead it return the lowest possible version ("0.0.0")
    """
    try:
        # remove release candidate suffix
        v = v.split("-")[0].split("rc")[0]
        return version.parse(v)
    except Exception:
        return version.parse("0.0.0")


def is_lnbits_version_ok(
    min_lnbits_version: Optional[str], max_lnbits_version: Optional[str]
) -> bool:
    if min_lnbits_version and (
        version_parse(min_lnbits_version) > version_parse(settings.version)
    ):
        return False
    if max_lnbits_version and (
        version_parse(max_lnbits_version) <= version_parse(settings.version)
    ):
        return False

    return True


def check_callback_url(url: str):
    netloc = urlparse(url).netloc
    for rule in settings.lnbits_callback_url_rules:
        if re.match(rule, netloc) is None:
            raise ValueError(
                f"Callback not allowed. URL: {url}. Netloc: {netloc}. Rule: {rule}"
            )


def download_url(url, save_path):
    with request.urlopen(url, timeout=60) as dl_file:
        with open(save_path, "wb") as out_file:
            out_file.write(dl_file.read())


def file_hash(filename):
    h = hashlib.sha256()
    b = bytearray(128 * 1024)
    mv = memoryview(b)
    with open(filename, "rb", buffering=0) as f:
        while n := f.readinto(mv):
            h.update(mv[:n])
    return h.hexdigest()


def get_api_routes(routes: list) -> dict[str, str]:
    data = {}
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        segments = route.path.split("/")
        if len(segments) < 3:
            continue
        if "/".join(segments[1:3]) == "api/v1":
            data["/".join(segments[0:4])] = segments[3].capitalize()
        elif "/".join(segments[2:4]) == "api/v1":
            data["/".join(segments[0:4])] = segments[1].capitalize()

    return data


def path_segments(path: str) -> list[str]:
    path = path.strip("/")
    segments = path.split("/")
    if len(segments) < 2:
        return segments
    if segments[0] == "upgrades":
        return segments[2:]
    return segments[0:]


def normalize_path(path: Optional[str]) -> str:
    path = path or ""
    return "/" + "/".join(path_segments(path))


def safe_upload_file_path(filename: str, directory: str = "images") -> Path:
    image_folder = Path(settings.lnbits_data_folder, directory)
    file_path = image_folder / filename
    # Prevent dir traversal attack
    if image_folder.resolve() not in file_path.resolve().parents:
        raise ValueError("Unsafe filename.")
    # Prevent filename with subdirectories
    file_path = image_folder / filename.split("/")[-1]
    return file_path.resolve()
