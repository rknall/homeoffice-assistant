// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
const APP_VERSION = '0.4.0-dev'
const APP_YEAR = new Date().getFullYear()
const GIT_COMMIT = __GIT_COMMIT__

export function Footer() {
  const versionDisplay = GIT_COMMIT !== 'unknown' ? `${APP_VERSION} (${GIT_COMMIT})` : APP_VERSION

  return (
    <footer className="py-4 px-6 text-center text-sm text-gray-500 border-t border-gray-200 bg-white">
      <div className="flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-4">
        <span className="font-medium text-gray-600">HomeOffice Assistant</span>
        <span className="hidden sm:inline text-gray-300">|</span>
        <span>Version {versionDisplay}</span>
        <span className="hidden sm:inline text-gray-300">|</span>
        <span>&copy; {APP_YEAR} All rights reserved</span>
      </div>
    </footer>
  )
}
