import os
import socket
import subprocess
import sys
import time
import urllib.error
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Literal, Optional, TypeVar, Union, overload
from urllib import request
from urllib.parse import urlencode


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class EnvVars:
    prettyurls: bool
    lang: str
    baseurl: Optional[str]
    dbhost: Optional[str]
    dbport: str
    dbuser: str
    dbpass: Optional[str]
    dbname: str
    tblpfx: str
    wtuser: Optional[str]
    wtname: Optional[str]
    wtpass: Optional[str]
    wtemail: Optional[str]
    # https://github.com/fisharebest/webtrees/blob/f9a3af650116d75f1a87f454cabff5e9047e43f3/app/Http/Middleware/UseDatabase.php#L71-L82
    dbkey: Optional[str]
    dbcert: Optional[str]
    dbca: Optional[str]
    dbverify: bool
    # php settings
    phpmemorylimit: str
    phpmaxexecutiontime: str
    phppostmaxsize: str
    phpuploadmaxfilesize: str
    trustedheaders: Optional[str]


def truish(value: Optional[str]) -> bool:
    """
    Check if a value is close enough to true
    """
    if value is None:
        return False

    return value.lower().strip() in ["true", "yes", "1"]


def print2(msg: Any) -> None:
    """
    Print a message to stderr.
    """
    print(f"[NV_INIT] {msg}", file=sys.stderr)


T = TypeVar("T")


@overload
def get_environment_variable(
    key: str, default: None = None, alternates: Optional[List[str]] = None
) -> Optional[str]: ...


@overload
def get_environment_variable(
    key: str, default: T = None, alternates: Optional[List[str]] = None
) -> T: ...


def get_environment_variable(
    key: str, default: Optional[T] = None, alternates: Optional[List[str]] = None
) -> Union[Optional[str], T]:
    """
    Try to find the value of an environment variable.
    """
    key = key.upper()

    # try to find variable in env
    if key in os.environ:
        value = os.environ[key]

        print2(f"{key} found in environment variables")
        return value

    # try to find file version of variable
    file_key = f"{key}_FILE"

    if file_key in os.environ:
        # file name does not exist
        if not os.path.isfile(os.environ[file_key]):
            print(f"WARNING: {file_key} is not a file: {os.environ[file_key]}")
            return None

        # read data from file
        with open(os.environ[file_key], "r") as f:
            value = f.read().strip()

        print2(f"{file_key} found in environment variables")
        return value

    # try to find alternate variable
    if alternates is not None:
        for a in alternates:
            a_value = get_environment_variable(a)
            if a_value is not None:
                return a_value

    # return default value
    print2(f"{key} NOT found in environment variables, using default: {default}")
    return default


ENV = EnvVars(
    prettyurls=truish(get_environment_variable("PRETTY_URLS")),
    lang=get_environment_variable("LANG", "en-US"),
    baseurl=get_environment_variable("BASE_URL"),
    dbhost=get_environment_variable("DB_HOST"),
    dbport=get_environment_variable("DB_PORT", "3306"),
    dbuser=get_environment_variable(
        "DB_USER",
        "webtrees",
        alternates=["MYSQL_USER", "MARIADB_USER", "POSTGRES_USER"],
    ),
    dbpass=get_environment_variable(
        "DB_PASS",
        alternates=["MYSQL_PASSWORD", "MARIADB_PASSWORD", "POSTGRES_PASSWORD"],
    ),
    dbname=get_environment_variable(
        "DB_NAME",
        default="webtrees",
        alternates=["MYSQL_DATABASE", "MARIADB_DATABASE", "POSTGRES_DB"],
    ),
    tblpfx=get_environment_variable("DB_PREFIX", "wt_"),
    wtuser=get_environment_variable("WT_USER"),
    wtname=get_environment_variable("WT_NAME"),
    wtpass=get_environment_variable("WT_PASS"),
    wtemail=get_environment_variable("WT_EMAIL"),
    dbkey=get_environment_variable("DB_KEY"),
    dbcert=get_environment_variable("DB_CERT"),
    dbca=get_environment_variable("DB_CA"),
    dbverify=truish(get_environment_variable("DB_VERIFY")),
    phpmemorylimit=get_environment_variable("PHP_MEMORY_LIMIT", "1024M"),
    phpmaxexecutiontime=get_environment_variable("PHP_MAX_EXECUTION_TIME", "90"),
    phppostmaxsize=get_environment_variable("PHP_POST_MAX_SIZE", "50M"),
    phpuploadmaxfilesize=get_environment_variable("PHP_UPLOAD_MAX_FILE_SIZE", "50M"),
    trustedheaders=get_environment_variable("TRUSTED_HEADERS", ""),
)


ROOT = "/var/www/webtrees"
DATA_DIR = os.path.join(ROOT, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.ini.php")
PHP_INI_FILE = "/usr/local/etc/php/php.ini"

os.chdir(ROOT)


def retry_urlopen(url: str, data: bytes) -> None:
    """
    Retry a request until a postiive repsonse code is reached. Raises error if it fails.
    """
    opener = request.build_opener(NoRedirect)
    request.install_opener(opener)

    for try_ in range(10):
        try:
            # make request
            print2(f"Attempt {try_} for {url}")
            resp = request.urlopen(url, data)
        except urllib.error.HTTPError as e:
            # capture error as well
            resp = e
            print2(f"Recieved HTTP {resp.status} response")

        # check status code
        # 302 is also accpetable in case the user selected something other than port 80
        if resp.status in (200, 302):
            return

        # backoff
        time.sleep(try_)

    raise RuntimeError(f"Could not send a request to {url}")


def add_line_to_file(filename: str, newline: str) -> None:
    """
    Add a new line to a file. If an existing line is found with the same
    starting string, it will be replaced.
    """
    newline += "\n"

    # read file
    with open(filename, "r") as fp:
        lines = fp.readlines()

    key = newline.split("=")[0]

    # replace matching line
    found = False

    for i, line in enumerate(lines):
        if line.startswith(key):
            if line == newline:
                return

            lines[i] = newline
            found = True
            break

    if not found:
        lines.append(newline)

    # write new contents
    with open(filename, "w") as fp:
        fp.writelines(lines)


def set_config_value(key: str, value: Optional[str]) -> None:
    """
    In the config file, make sure the given key is set to the given value.
    """
    if value is None:
        return

    print2(f"Setting value for {key} in config")

    if not os.path.isfile(CONFIG_FILE):
        print2(f"WARNING: {CONFIG_FILE} does not exist")
        return

    add_line_to_file(CONFIG_FILE, f'{key}="{value}"')


def set_php_ini_value(key: str, value: str) -> None:
    """
    In the php.ini file, make sure the given key is set to the given value.
    """
    print2(f"Setting value for {key} in php.ini")
    add_line_to_file(PHP_INI_FILE, f"{key} = {value}")


def perms() -> None:
    """
    Set up folder permissions
    """
    if os.path.isfile(CONFIG_FILE):
        subprocess.check_call(["chmod", "700", CONFIG_FILE])


def php_ini() -> None:
    """
    Update PHP .ini file
    """
    print2("Updating php.ini")

    if not os.path.isfile(PHP_INI_FILE):
        print2("Creating php.ini")

        os.makedirs(os.path.dirname(PHP_INI_FILE), exist_ok=True)
        with open(PHP_INI_FILE, "w") as fp:
            fp.writelines(["[PHP]\n", "\n"])

    set_php_ini_value("memory_limit", ENV.phpmemorylimit)
    set_php_ini_value("max_execution_time", ENV.phpmaxexecutiontime)
    set_php_ini_value("post_max_size", ENV.phppostmaxsize)
    set_php_ini_value("upload_max_filesize", ENV.phpuploadmaxfilesize)


def check_db_variables() -> bool:
    """
    Check if all required database variables are present
    """
    try:
        assert ENV.dbname is not None
        assert ENV.tblpfx is not None

        assert ENV.dbhost is not None
        assert ENV.dbport is not None
        assert ENV.dbuser is not None
        assert ENV.dbpass is not None

    except AssertionError:
        print2("WARNING: Not all database variables are set")
        return False

    return True


def setup_wizard() -> None:
    """
    Run the setup wizard
    """

    if os.path.isfile(CONFIG_FILE):
        return

    print2("Attempting to automate setup wizard")

    # make sure all the variables we need are not set to None
    if not check_db_variables():
        return

    if any(
        v is None
        for v in [ENV.wtname, ENV.wtuser, ENV.wtpass, ENV.wtemail]
    ):
        print2("WARNING: Not all required variables were found for setup wizard")
        return

    print2("Automating setup wizard")
    print2("Starting Apache in background")
    # run apache in the background
    apache_proc = subprocess.Popen(["apache2-foreground"], stderr=subprocess.DEVNULL)

    # for typing, check_db_variables already does this
    assert ENV.dbhost is not None

    # try to resolve the host
    # most common error is wrong hostname
    try:
        socket.gethostbyname(ENV.dbhost)
    except socket.gaierror:
        print2(f"ERROR: Could not resolve database host '{ENV.dbhost}'")
        print2(
            "ERROR: You likely have the DBHOST environment variable set incorrectly."
        )
        print2("ERROR: Exiting.")

        # stop apache
        apache_proc.terminate()
        # die
        sys.exit(1)

    # https://dev.mysql.com/doc/refman/8.0/en/mysqladmin.html#option_mysqladmin_user
    # don't miss the capital &
    cmd = ["mysqladmin", "ping", "-h", ENV.dbhost, "-P", ENV.dbport, "--silent"]
    name = "MySQL"

    while subprocess.run(cmd).returncode != 0:
        print2(f"Waiting for {name} server {ENV.dbhost}:{ENV.dbport} to be ready")
        time.sleep(1)

    # send it
    url = "http://127.0.0.1:8080/"
    print2(f"Sending setup wizard request to {url}")

    retry_urlopen(
        url,
        urlencode(
            {
                "lang": ENV.lang,
                "tblpfx": ENV.tblpfx,
                "dbtype": "mysql",
                "dbhost": ENV.dbhost,
                "dbport": ENV.dbport,
                "dbuser": ENV.dbuser,
                "dbpass": ENV.dbpass,
                "dbname": ENV.dbname,
                "wtname": ENV.wtname,
                "wtuser": ENV.wtuser,
                "wtpass": ENV.wtpass,
                "wtemail": ENV.wtemail,
                "step": "6",
            }
        ).encode("ascii"),
    )

    print2("Stopping Apache")
    apache_proc.terminate()


def update_config_file() -> None:
    """
    Update the config file with items set via environment variables
    """
    print2("Updating config file")

    if not os.path.isfile(CONFIG_FILE):
        print2(f"Config file not found at {CONFIG_FILE}. Nothing to update.")
        return

    # update independent values
    set_config_value("rewrite_urls", str(int(ENV.prettyurls)))
    set_config_value("base_url", ENV.baseurl)
    if ENV.trustedheaders != "":
        set_config_value("trusted_headers", ENV.trustedheaders)

    # update database values as a group
    if check_db_variables():
        set_config_value("dbhost", ENV.dbhost)
        set_config_value("dbport", ENV.dbport)
        set_config_value("dbuser", ENV.dbuser)
        set_config_value("dbpass", ENV.dbpass)
        set_config_value("dbname", ENV.dbname)
        set_config_value("tblpfx", ENV.tblpfx)

    # update databases verification values
    if all(v is not None for v in [ENV.dbkey, ENV.dbcert, ENV.dbca]):
        set_config_value("dbkey", ENV.dbkey)
        set_config_value("dbcert", ENV.dbcert)
        set_config_value("dbca", ENV.dbca)
        set_config_value("dbverify", str(int(ENV.dbverify)))


def htaccess() -> None:
    """
    Recreate .htaccess file if it ever deletes itself in the /data/ directory
    """
    htaccess_file = os.path.join(DATA_DIR, ".htaccess")

    if os.path.isfile(htaccess_file):
        return

    print2(f"WARNING: {htaccess_file} does not exist")

    with open(htaccess_file, "w") as fp:
        fp.writelines(["order allow,deny", "deny from all"])

    print2(f"Created {htaccess_file}")


def main() -> None:
    # create php config
    php_ini()
    # run the setup wizard if the config file doesn't exist
    setup_wizard()
    # update the config file
    update_config_file()
    # make sure .htaccess exists
    htaccess()
    # enforce config permissions
    perms()

    print2("Starting Apache")
    subprocess.run(["apache2-foreground"], stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
