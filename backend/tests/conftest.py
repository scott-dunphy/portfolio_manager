import os
import sys
import types

# Ensure the backend package root is on sys.path so `services.*` imports work in tests.
TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(TESTS_DIR, '..'))

if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Provide a lightweight stub for flask_sqlalchemy so modules that import the real extension
# can still be imported in unit tests without requiring the full dependency stack.
if 'flask_sqlalchemy' not in sys.modules:
    flask_sqlalchemy = types.ModuleType('flask_sqlalchemy')

    class SQLAlchemy:  # pragma: no cover - simple stub
        class Model:
            pass

        def __init__(self, *_, **__):
            pass

    flask_sqlalchemy.SQLAlchemy = SQLAlchemy
    sys.modules['flask_sqlalchemy'] = flask_sqlalchemy


# Stub out the `models` module used for type hints so service modules can be imported
# without initializing the real ORM layer. Our unit tests construct lightweight stand-ins
# for the domain objects directly.
if 'models' not in sys.modules:
    models = types.ModuleType('models')

    class Portfolio:  # pragma: no cover - simple stub
        query = None

    class Property:
        query = None

    class Loan:
        query = None

    class CashFlow:
        query = None

    models.Portfolio = Portfolio
    models.Property = Property
    models.Loan = Loan
    models.CashFlow = CashFlow
    sys.modules['models'] = models
