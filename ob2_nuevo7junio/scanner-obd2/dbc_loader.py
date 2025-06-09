"""
dbc_loader.py - Utilidades para cargar archivos DBC y preparar el entorno de simulación CAN
"""
import os
import cantools

def load_dbc(file_path):
    """
    Carga un archivo DBC usando cantools y retorna el objeto Database.
    Args:
        file_path (str): Ruta al archivo DBC
    Returns:
        cantools.database.Database: Objeto de base de datos DBC
    """
    return cantools.database.load_file(file_path)

def ensure_dbc_folder():
    """
    Verifica que exista la carpeta /dbc_files/ y crea un DBC de ejemplo si está vacía.
    """
    dbc_dir = os.path.join(os.path.dirname(__file__), 'dbc_files')
    os.makedirs(dbc_dir, exist_ok=True)
    files = [f for f in os.listdir(dbc_dir) if f.endswith('.dbc')]
    if not files:
        # Crear un DBC de ejemplo mínimo
        example_dbc = """
VERSION "1.0"
NS_ :
    NS_DESC_
    CM_
    BA_DEF_
    BA_
    VAL_
    CAT_DEF_
    CAT_
    FILTER
    BA_DEF_DEF_
    EV_DATA_
    ENVVAR_DATA_
    SGTYPE_
    SGTYPE_VAL_
    BA_DEF_SGTYPE_
    BA_SGTYPE_
    SIG_TYPE_REF_
    VAL_TABLE_
    SIG_GROUP_
    SIG_VALTYPE_
    SIGTYPE_VALTYPE_
    BO_TX_BU_
    BA_DEF_REL_
    BA_REL_
    BA_DEF_DEF_REL_
    BU_SG_REL_
    BU_EV_REL_
    BU_BO_REL_
    SG_MUL_VAL_
BS_:
BU_: ECU1 ECU2
BO_ 100 ExampleMessage: 8 ECU1
 SG_ ExampleSignal : 0|8@1+ (1,0) [0|255] "kmh"  ECU1
CM_ SG_ 100 ExampleSignal "Velocidad simulada";
"""
        with open(os.path.join(dbc_dir, 'example.dbc'), 'w') as f:
            f.write(example_dbc)
    return dbc_dir
