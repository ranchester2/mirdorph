pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'mirdorph')
plugindir = join_paths(moduledir, 'plugins')
gnome = import('gnome')
python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'mirdorph.in',
  output: 'mirdorph',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

mirdorph_sources = [
  '__init__.py',
  'main.py',
  'login_window.py',
  'main_window.py',
  'event_manager.py',
  'event_receiver.py',
  'channel_inner_window.py',
  'message_view.py',
  'message.py',
  'message_parsing.py',
  'message_entry_bar.py',
  'attachment.py',
  'channel_sidebar.py',
  'confman.py',
  'channel_properties_window.py',
  'typing_indicator.py',
  'settings_window.py',
  'link_preview.py',
  'image_viewer.py',
  'plugin.py'
]

install_data(mirdorph_sources, install_dir: moduledir)

subdir('disc_cogs')
subdir('plugins')
