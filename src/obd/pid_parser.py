"""
Parser universal para PIDs OBD-II con soporte para fórmulas dinámicas y perfiles propietarios.
"""
import logging
import json
import csv
from typing import Dict, Any, Optional, List, Union, Callable
from pathlib import Path
import math
import operator

class PIDParserError(Exception):
    """Excepción base para errores de parsing de PID."""
    pass

class PIDDefinition:
    """Definición completa de un PID OBD-II."""
    def __init__(self, pid: str, name: str, description: str,
                 bytes_returned: int, formula: str,
                 min_value: float, max_value: float,
                 units: str, is_proprietary: bool = False):
        self.pid = pid
        self.name = name
        self.description = description
        self.bytes_returned = bytes_returned
        self.formula = formula
        self.min_value = min_value
        self.max_value = max_value
        self.units = units
        self.is_proprietary = is_proprietary
        
class PIDParser:
    """
    Parser universal para PIDs OBD-II con fórmulas dinámicas y perfiles propietarios.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pids: Dict[str, PIDDefinition] = {}
        self.proprietary_profiles: Dict[str, Dict[str, PIDDefinition]] = {}
        
        # Operadores soportados en fórmulas dinámicas
        self.operators = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.truediv,
            '**': operator.pow,
            'sqrt': math.sqrt,
            'abs': abs
        }
        
    def load_standard_pids(self, filepath: Union[str, Path]):
        """
        Carga PIDs estándar desde archivo CSV.
        
        Args:
            filepath: Ruta al archivo CSV con definiciones estándar
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pid = PIDDefinition(
                        pid=row['pid'],
                        name=row['name'],
                        description=row['description'],
                        bytes_returned=int(row['bytes']),
                        formula=row['formula'],
                        min_value=float(row['min']),
                        max_value=float(row['max']),
                        units=row['units']
                    )
                    self.pids[row['pid']] = pid
            self.logger.info(f"Cargados {len(self.pids)} PIDs estándar")
        except Exception as e:
            self.logger.error(f"Error cargando PIDs estándar: {e}")
            raise
            
    def load_proprietary_profile(self, profile_name: str, filepath: Union[str, Path]):
        """
        Carga perfil propietario desde archivo JSON.
        
        Args:
            profile_name: Nombre identificador del perfil
            filepath: Ruta al archivo JSON con definiciones propietarias
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                profile = json.load(f)
                pid_dict = {}
                
                for pid_def in profile['pids']:
                    pid = PIDDefinition(
                        pid=pid_def['pid'],
                        name=pid_def['name'],
                        description=pid_def.get('description', ''),
                        bytes_returned=pid_def['bytes'],
                        formula=pid_def['formula'],
                        min_value=float(pid_def.get('min', 0)),
                        max_value=float(pid_def.get('max', 0)),
                        units=pid_def.get('units', ''),
                        is_proprietary=True
                    )
                    pid_dict[pid_def['pid']] = pid
                    
                self.proprietary_profiles[profile_name] = pid_dict
                self.logger.info(f"Cargado perfil propietario '{profile_name}' con {len(pid_dict)} PIDs")
        except Exception as e:
            self.logger.error(f"Error cargando perfil propietario: {e}")
            raise
            
    def parse_response(self, pid: str, response: str,
                      profile_name: Optional[str] = None) -> Optional[float]:
        """
        Parsea respuesta OBD-II usando definición de PID.
        
        Args:
            pid: PID a parsear
            response: Respuesta cruda del ELM327
            profile_name: Nombre del perfil propietario (opcional)
            
        Returns:
            Valor parseado según fórmula o None si error
        """
        try:
            # Buscar definición de PID
            pid_def = None
            if profile_name and profile_name in self.proprietary_profiles:
                pid_def = self.proprietary_profiles[profile_name].get(pid)
            if not pid_def:
                pid_def = self.pids.get(pid)
            if not pid_def:
                raise PIDParserError(f"PID {pid} no encontrado")
                
            # Extraer bytes de respuesta
            clean_resp = response.replace(' ', '').replace('\r', '').replace('\n', '')
            if not clean_resp.startswith('41'):
                raise PIDParserError(f"Respuesta inválida: {response}")
                
            data_bytes = []
            resp_data = clean_resp[4:4 + pid_def.bytes_returned * 2]
            for i in range(0, len(resp_data), 2):
                data_bytes.append(int(resp_data[i:i+2], 16))
                
            if len(data_bytes) != pid_def.bytes_returned:
                raise PIDParserError(f"Cantidad de bytes incorrecta: {len(data_bytes)} != {pid_def.bytes_returned}")
                
            # Evaluar fórmula dinámica
            result = self._evaluate_formula(pid_def.formula, data_bytes)
            
            # Validar rango
            if result < pid_def.min_value or result > pid_def.max_value:
                self.logger.warning(f"Valor fuera de rango para {pid}: {result}")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error parseando PID {pid}: {e}")
            return None
            
    def _evaluate_formula(self, formula: str, values: List[int]) -> float:
        """
        Evalúa fórmula dinámica usando valores de bytes.
        
        Args:
            formula: Fórmula como string (ej: "A*256+B/4")
            values: Lista de valores de bytes [A, B, C, ...]
            
        Returns:
            Resultado de la evaluación
        """
        # Reemplazar variables con valores
        var_map = {}
        for i, val in enumerate(values):
            var_name = chr(65 + i)  # A, B, C, ...
            var_map[var_name] = val
            
        # Construir y evaluar expresión segura
        try:
            # Dividir en tokens y validar
            tokens = self._tokenize_formula(formula)
            return self._evaluate_tokens(tokens, var_map)
        except Exception as e:
            raise PIDParserError(f"Error evaluando fórmula '{formula}': {e}")
            
    def _tokenize_formula(self, formula: str) -> List[str]:
        """
        Divide fórmula en tokens seguros.
        
        Args:
            formula: Fórmula a tokenizar
            
        Returns:
            Lista de tokens válidos
        """
        import re
        tokens = []
        current = ""
        
        for char in formula:
            if char.isspace():
                continue
            if char in '+-*/()':
                if current:
                    tokens.append(current)
                    current = ""
                tokens.append(char)
            else:
                current += char
        if current:
            tokens.append(current)
            
        return tokens
        
    def _evaluate_tokens(self, tokens: List[str], var_map: Dict[str, float]) -> float:
        """
        Evalúa tokens de forma segura.
        
        Args:
            tokens: Lista de tokens
            var_map: Mapeo de variables a valores
            
        Returns:
            Resultado de la evaluación
        """
        # Implementar evaluador de expresiones simple y seguro
        # Esta es una implementación básica - en producción usar
        # una biblioteca de evaluación de expresiones matemáticas
        stack = []
        
        for token in tokens:
            if token in self.operators:
                b = stack.pop()
                a = stack.pop()
                stack.append(self.operators[token](a, b))
            elif token in var_map:
                stack.append(float(var_map[token]))
            else:
                try:
                    stack.append(float(token))
                except ValueError:
                    raise PIDParserError(f"Token inválido: {token}")
                    
        return stack[0] if stack else 0.0
