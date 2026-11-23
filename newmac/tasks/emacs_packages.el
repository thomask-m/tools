;;; emacs_packages.el --- check or install the packages ~/.emacs needs  -*- lexical-binding: t -*-
;;
;; Run in batch mode by the emacs-packages task:
;;   Emacs --batch -l emacs_packages.el                          # print missing packages
;;   Emacs --batch --eval '(setq newmac-install t)' -l emacs_packages.el   # install them
;;
;; The package list is `package-selected-packages' from ~/.emacs.custom.el.
;; ~/.emacs itself isn't loaded: it `require's those packages, which fails
;; until they're installed.

(defvar newmac-install nil "Non-nil means install missing packages, not just list them.")

(setq custom-file (expand-file-name "~/.emacs.custom.el"))
(load custom-file nil t)

(require 'package)
(add-to-list 'package-archives '("melpa" . "https://melpa.org/packages/") t)
(package-initialize)

(let ((missing (seq-remove #'package-installed-p package-selected-packages))
      (failed nil))
  (if (not newmac-install)
      (dolist (pkg missing) (princ (format "%s\n" pkg)))
    (when missing
      (package-refresh-contents)
      (dolist (pkg missing)
        (message "Installing %s..." pkg)
        (condition-case err
            (package-install pkg)
          (error (push pkg failed)
                 (message "Failed to install %s: %s" pkg (error-message-string err))))))
    (when failed
      (message "Could not install: %s" (mapconcat #'symbol-name (nreverse failed) " "))
      (kill-emacs 1))))
