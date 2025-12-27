.PHONY: postgres postgres-stop preseed clean

# Delegate to api/Makefile
postgres postgres-stop preseed clean:
	$(MAKE) -C api $@
