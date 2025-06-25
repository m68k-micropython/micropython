#include <py/obj.h>
#include "Multiverse.h"

void check_mac_err(OSErr e);
MP_NORETURN void raise_mac_err(OSErr e);
int convert_mac_err(OSErr e);
mp_obj_t new_str_from_pstr(Byte *pStr);
mp_obj_t new_bytes_from_pstr(Byte *pStr);
Byte *pstr_from_str(Byte *pStr, size_t pStr_size, mp_obj_t obj);
Byte *pstr_from_data(Byte *pStr, size_t pStr_size, const char *str_data, size_t str_len);
Byte *pstr_from_cstr(Byte *pStr, size_t pStr_size, const char *str_data);
Byte *pstr_cat_str(Byte *pStr, size_t pStr_size, mp_obj_t obj);
Byte *pstr_cat_cstr(Byte *pStr, size_t pStr_size, const char *str_data);
Byte *pstr_cat_data(Byte *pStr, size_t pStr_size, const char *str_data, size_t str_len);

#define PSTR_FROM_STR(pStr, obj) pstr_from_str(pStr, MP_ARRAY_SIZE(pStr), obj)
#define PSTR_FROM_CSTR(pStr, str) pstr_from_cstr(pStr, MP_ARRAY_SIZE(pStr), str)
#define PSTR_FROM_DATA(pStr, ptr, len) pstr_from_data(pStr, MP_ARRAY_SIZE(pStr), ptr, len)

#define PSTR_LEN(p) (*(p))
#define PSTR_DATA(p) ((char *)((p) + 1))
