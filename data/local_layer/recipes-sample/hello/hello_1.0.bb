DESCRIPTION = "This package contains the simple Hello World program."
LICENSE = "windriver"
LICENSE_FLAGS = "commercial_windriver"
LIC_FILES_CHKSUM = "file://hello.c;beginline=1;endline=3;md5=3e8f741b049bec8146c81a2667ab4b45"

SECTION = "sample"

PR = "r1"

SRC_URI = "file://hello.c"

S = "${WORKDIR}"

do_compile() {
  ${CC} ${CFLAGS} ${LDFLAGS} -o hello hello.c
}

do_install() {
  install -d ${D}${bindir}
  install -m 0755 hello ${D}${bindir}
}
