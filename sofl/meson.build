moduledir = python_dir / 'sofl'

configure_file(
  input: 'sofl.in',
  output: 'sofl',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
)

install_subdir('importer', install_dir: moduledir)
install_subdir('utils', install_dir: moduledir)
install_subdir('store', install_dir: moduledir)
install_subdir('logging', install_dir: moduledir)
install_subdir('errors', install_dir: moduledir)
install_subdir('dialogs', install_dir: moduledir)
install_subdir('installer', install_dir: moduledir)
install_data(
  [
    'application_delegate.py',
    'main.py',
    'window.py',
    'preferences.py',
    'details_dialog.py',
    'game.py',
    'game_cover.py',
    'game_factory.py',
    'onlinefix_game.py',
    'game_data.py',
    configure_file(input: 'shared.py.in', output: 'shared.py', configuration: conf),
  ],
  install_dir: moduledir,
)
