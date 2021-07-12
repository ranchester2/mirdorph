project('mirdorph',
          version: '0.13.0',
    meson_version: '>= 0.50.0',
  default_options: [ 'warning_level=2',
                   ],
)

i18n = import('i18n')

description = 'A client for Discord'
prettyname = 'Mirdorph'
authorfullname = 'Raidro Manchester'
app_id = 'org.gnome.gitlab.ranchester.Mirdorph'
contributors = '\n'.join([
    'Raidro Manchester'
])

subdir('data')
subdir('src')
subdir('po')

meson.add_install_script('build-aux/meson/postinstall.py')
