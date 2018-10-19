# Settings for the installer

# type:  restapi-web   - REST API from a LayerIndex-web
#        restapi-files - REST API, but only from files
#        export        - Exported DB from a LayerIndex-web -- reads file(s)

# url/path may contain:
#  #INSTALL_DIR# which is replaced by the setup directory
#  #BASE_URL# which is replaced by the base url for setup directory
#  #BASE_BRANCH# which is replaced by the base branch for the setup directory

# Since we know the url below will be mirrored to our
# internal git mirrors, change format so it can be replaced
# with the proper value(s)
REPLACE = [
    ( 'git://lxgit.wrs.com', '#BASE_URL#' )
]

INDEXES = [
    {
        'DESCRIPTION' : 'Wind River Developer Layer Index',
        'TYPE' : 'restapi-web',
        'URL' : 'http://layers.wrs.com/layerindex/api/',
        'CACHE' : 'config/index-cache/layers_wrs_com',
    },
#    {
#        'DESCRIPTION' : 'OpenEmbedded Layer Index',
#        'TYPE' : 'restapi-web',
#        'URL' : 'http://layers.openembedded.org/layerindex/api/',
#        'CACHE' : 'config/index-cache/layers_openembedded_org',
#        'BRANCH' : 'morty'
#    },
]

# Bitbake URL on the same server at openembedded-core
# bitbake is assumed to be at the same basepath as OpenEmbedded-Core
BITBAKE = "bitbake"

# Base Layers (these layers and their dependencies are -always- included)
BASE_LAYERS = "wrlinux"

DEFAULT_DISTRO = "wrlinux"
DEFAULT_MACHINE = "qemux86-64"

# Default number of repo jobs
REPO_JOBS = 4

# Repo remote name list
REMOTES = [
    ( 'git://git.openembedded.org', 'openembedded' ),
    ( 'git://git.yoctoproject.org', 'yoctoproject' ),
    ( 'http://git.yoctoproject.org', 'http_yoctoproject' ),
    ( 'git://github.com', 'github' ),
    ( 'https://github.com', 'https_github' ),
]

# The default tag used to filter the output of --list actions. 'all' means no
# filter
DEFAULT_LAYER_COMPAT_TAG = "wrl"

# required host tools to build out project
# Do not edit this manually, it is updated automatically.
REQUIRED_HOSTTOOLS = """
    [ ar as awk basename bash bzip2 cat chgrp chmod chown chrpath
    cmp comm cp cpio cpp cut date dd diff diffstat dirname du echo
    egrep env expand expr false fgrep file find flock g++ gawk gcc
    getconf getopt git grep gunzip gzip head hostname iconv id install
    ld ldd ln ls make makeinfo md5sum mkdir mknod mktemp mv nm objcopy
    objdump od patch perl pod2man pr printf pwd python2 python2.7
    python3 ranlib readelf readlink realpath rm rmdir rpcgen sed seq
    sh sha256sum sleep sort split stat strings strip tail tar tee
    test touch tr true uname uniq wc wget which xargs
"""
