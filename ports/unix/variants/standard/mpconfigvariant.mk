# This is the default variant when you `make` the Unix port.

FROZEN_MANIFEST ?= $(VARIANT_DIR)/manifest.py

include $(TOP)/extmod/multiversal.mk
$(eval $(call multiversal_module,mkapitest,variants/coverage/mkapi_test.yaml))
