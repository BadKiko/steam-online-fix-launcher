# Heavily inspired by https://gitlab.gnome.org/World/lollypop/-/blob/master/search-provider/meson.build

service_dir = join_paths(get_option('datadir'), 'dbus-1', 'services')
search_provider_dir = join_paths(get_option('datadir'), 'gnome-shell', 'search-providers')

search_provider_id = app_id + '.SearchProvider'

conf_data = configuration_data()
conf_data.set('APP_ID', app_id)
conf_data.set('bindir', join_paths(get_option('prefix'), get_option('bindir')))
conf_data.set('PREFIX', prefix)
conf_data.set('PYTHON', py_installation.full_path())

search_provider_executable = configure_file(
    input: 'sofl-search-provider.in',
    output: app_id + '-search-provider',
    configuration: conf_data,
    install: true,
    install_dir: get_option('bindir')
)

service_file = configure_file(
    input: 'org.badkiko.sofl.SearchProvider.service.in',
    output: app_id + '.SearchProvider.service',
    configuration: conf_data,
    install: true,
    install_dir: join_paths(get_option('datadir'), 'dbus-1/services')
)

search_provider_file = configure_file(
    input: 'org.badkiko.sofl.SearchProvider.ini',
    output: search_provider_id + '.ini',
    configuration: conf_data,
    install: true,
    install_dir: join_paths(get_option('datadir'), 'gnome-shell/search-providers')
)
