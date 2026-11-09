# Sprites v1 native host. The binary and bundle are derived (build/, never committed).
# `make install` -> ~/Applications/Sprites.app; `make install-agent` loads the LaunchAgent (owner's call).
SWIFTC  ?= /usr/bin/swiftc
SOURCES := Config.swift Decide.swift Aether.swift AetherHost.swift Native.swift CGCanvas.swift Stage.swift Focus.swift Activate.swift Settings.swift Backdrop.swift App.swift
BUILD   ?= build
APP     := $(BUILD)/Sprites.app
DEST    := $(HOME)/Applications/Sprites.app
SPRITES := $(abspath $(CURDIR)/../..)
AGENT   := $(HOME)/Library/LaunchAgents/com.mandrake.sprites.plist

# Signing (review R1_MACOS #5): ad hoc pins the iTerm2 Automation grant to one cdhash, so every rebuild re-prompts. A
# stable self-signed identity gives a designated requirement on the certificate, which survives rebuilds and tree
# switches. `make signing-identity` makes it once, in its own keychain under the agent storage root (not the login
# keychain); without it the build falls back to ad hoc and says so.
SIGN_NAME     ?= Sprites Local Signing
SIGN_KEYCHAIN ?= $(HOME)/agent-storage/sprites/signing/sprites-signing.keychain-db
SIGN_PASS     ?= sprites-local-signing
# codesign finds an identity only in the user keychain search list: the keychain is added for the one call, then the
# list is put back as it was. sign_app DIR: the identity's SHA-1 if made, else ad hoc ("-").
define sign_app
	@id=$$(security find-identity -p codesigning "$(SIGN_KEYCHAIN)" 2>/dev/null | awk '/"$(SIGN_NAME)"/ {print $$2; exit}'); \
	if [ -n "$$id" ]; then \
	  security unlock-keychain -p "$(SIGN_PASS)" "$(SIGN_KEYCHAIN)"; \
	  old=$$(security list-keychains -d user | tr -d '"' | xargs); \
	  security list-keychains -d user -s $$old "$(SIGN_KEYCHAIN)"; \
	  codesign --force --sign "$$id" --keychain "$(SIGN_KEYCHAIN)" --entitlements Sprites.entitlements $(1); rc=$$?; \
	  security list-keychains -d user -s $$old; [ $$rc -eq 0 ] || exit $$rc; \
	  echo "signed $(1) with $(SIGN_NAME) ($$id)"; \
	else \
	  codesign --force --sign - --entitlements Sprites.entitlements $(1) >/dev/null 2>&1 || true; \
	  echo "signed $(1) ad hoc: run 'make signing-identity' once, or every rebuild re-asks for Automation"; \
	fi
endef

.PHONY: all app install install-agent uninstall-agent clean signing-identity
all: app

$(BUILD)/Sprites: $(SOURCES)
	@mkdir -p $(BUILD)
	$(SWIFTC) -O -swift-version 5 -parse-as-library -target arm64-apple-macos13.0 \
	    -framework AppKit -framework WebKit -framework Carbon -framework Metal -framework QuartzCore -framework JavaScriptCore $(SOURCES) -o $@

app: $(BUILD)/Sprites Info.plist Sprites.entitlements
	@mkdir -p $(APP)/Contents/MacOS
	cp $(BUILD)/Sprites $(APP)/Contents/MacOS/Sprites
	cp Info.plist $(APP)/Contents/Info.plist
	plutil -replace SpritesHome -string "$(SPRITES)" $(APP)/Contents/Info.plist
	$(call sign_app,$(APP))

install: app
	@mkdir -p $(HOME)/Applications
	rm -rf $(DEST)
	cp -R $(APP) $(DEST)
	$(call sign_app,$(DEST))
	@echo installed $(DEST)

signing-identity:
	@if security find-identity -p codesigning "$(SIGN_KEYCHAIN)" 2>/dev/null | grep -q '"$(SIGN_NAME)"'; then echo "have $(SIGN_NAME)"; exit 0; fi; \
	set -e; d=$$(dirname "$(SIGN_KEYCHAIN)"); mkdir -p "$$d"; chmod 700 "$$d"; t=$$(mktemp -d "$$d/mk.XXXXXX"); \
	printf '[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=$(SIGN_NAME)\n[ext]\nbasicConstraints=critical,CA:false\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=critical,codeSigning\n' > $$t/c.cnf; \
	openssl req -x509 -newkey rsa:2048 -nodes -keyout $$t/k.pem -out $$t/c.pem -days 7300 -config $$t/c.cnf 2>/dev/null; \
	openssl pkcs12 -export -legacy -inkey $$t/k.pem -in $$t/c.pem -out $$t/i.p12 -passout pass:x 2>/dev/null || \
	  openssl pkcs12 -export -inkey $$t/k.pem -in $$t/c.pem -out $$t/i.p12 -passout pass:x; \
	[ -f "$(SIGN_KEYCHAIN)" ] || security create-keychain -p "$(SIGN_PASS)" "$(SIGN_KEYCHAIN)"; \
	security set-keychain-settings "$(SIGN_KEYCHAIN)"; security unlock-keychain -p "$(SIGN_PASS)" "$(SIGN_KEYCHAIN)"; \
	security import $$t/i.p12 -k "$(SIGN_KEYCHAIN)" -P x -T /usr/bin/codesign >/dev/null; \
	security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$(SIGN_PASS)" "$(SIGN_KEYCHAIN)" >/dev/null; \
	rm -rf $$t; echo "made $(SIGN_NAME) in $(SIGN_KEYCHAIN)"

install-agent: install
	@mkdir -p $(HOME)/Library/LaunchAgents $(HOME)/agent-storage/sprites/logs
	sed "s#__HOME__#$(HOME)#g" com.mandrake.sprites.plist > $(AGENT)
	plutil -lint $(AGENT)
	-launchctl bootout gui/$$(id -u) $(AGENT) 2>/dev/null
	launchctl bootstrap gui/$$(id -u) $(AGENT)
	@echo loaded com.mandrake.sprites

uninstall-agent:
	-launchctl bootout gui/$$(id -u) $(AGENT)
	rm -f $(AGENT)

clean:
	rm -rf $(BUILD)
