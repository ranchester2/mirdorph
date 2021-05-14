pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'mirdorph')
gnome = import('gnome')

subdir('ui')
app_resources = gnome.compile_resources(
  'mirdorph',
  'mirdorph.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: [
    configure_file(
      input: 'ui/about_dialog.ui.in',
      output: 'about_dialog.ui',
      configuration: glade_conf
    )
  ]
)

desktop_file = i18n.merge_file(
  input: 'org.gnome.gitlab.ranchester.Mirdorph.desktop.in',
  output: 'org.gnome.gitlab.ranchester.Mirdorph.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
endif

appstream_file = i18n.merge_file(
  input: 'org.gnome.gitlab.ranchester.Mirdorph.appdata.xml.in',
  output: 'org.gnome.gitlab.ranchester.Mirdorph.appdata.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'appdata')
)

# Here because else appstream complains about missing icons

subdir('icons')
appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util,
    args: ['validate', appstream_file]
  )
endif

install_data('org.gnome.gitlab.ranchester.Mirdorph.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

