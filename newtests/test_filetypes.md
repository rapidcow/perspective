FileTypeContext tests
=====================

TEST 1: default value
---------------------

a default context MUST have these properties:

*  ctx.is_text_type('plain') == True
*  ctx.is_text_type('binary') == False
*  ctx.get_default_extension('plain') == '.txt'
*  ctx.get_default_extension('binary') raises LookupError
*  ...
