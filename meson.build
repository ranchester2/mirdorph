project('mirdorph',
          version: '0.0.3',
    meson_version: '>= 0.50.0',
  default_options: [ 'warning_level=2',
                   ],
)

description = 'A client for Discord'
prettyname = 'Mirdorph'
authorfullname = 'Raidro Manchester'
app_version = meson.project_version()
app_id = 'org.gnome.gitlab.ranchester.Mirdorph'
contributors = '\n'.join([
    'Raidro Manchester'
])

i18n = import('i18n')
python = import('python')
py_installation = python.find_installation('python3')
if not py_installation.found()
    error('No valid python3 binary found')
endif
pythondir = py_installation.get_install_dir()


subdir('data')
subdir('src')
subdir('po')

meson.add_install_script('build-aux/meson/postinstall.py')
