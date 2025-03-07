{pkgs}: {
  deps = [
    pkgs.python312Packages.autopep8
    pkgs.mailutils
    pkgs.glibcLocales
  ];
}
