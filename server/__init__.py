"""OCR Studio web backend (FastAPI).

A thin HTTP layer over the existing Qt-free core in ``modules/`` — it does not
import PyQt5. Run with::

    uvicorn server.main:app --reload
"""
