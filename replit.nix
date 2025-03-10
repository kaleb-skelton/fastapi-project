{pkgs}: {
  deps = [
    pkgs.libxcrypt
    pkgs.python312Packages.autopep8
    pkgs.mailutils
    pkgs.glibcLocales
  ];
}
