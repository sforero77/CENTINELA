"""Cada umbral de vejez tiene que corresponder a cómo se escribe su fichero.

DOS FICHEROS QUE NO SE ESCRIBEN IGUAL COMPARTIAN UMBRAL.

`status.json` es un **latido**: se escribe cada corrida del vigia haya o no
novedad, asi que doce horas de silencio significan que el cron se paro.
`observados.json` es **escritura por cambio**: `cli.py` compara la lista de
`usgs_id` y solo commitea si entro o salio un evento. Un dia sin sismos menores
en LATAM lo deja quieto con toda razon.

Medido sobre los 68 huecos reales entre escrituras desde el 26-ago-2026:
mediana 1,1 h, p90 7,4 h, **maximo 12,8 h**. El maximo ya se paso del umbral de
12 h. No salto de milagro —`frescura.yml` corre cada tres horas y el hueco cayo
entre dos pasadas— pero habria dicho que la capa estaba congelada cuando lo
unico que pasaba es que no habia temblado.

Una alarma que se equivoca es peor que no tenerla, y este proyecto ya lo tiene
escrito en `frescura.yml`: un aviso que sigue abierto cuando el problema se fue
enseña a no creerselo.
"""

from __future__ import annotations

from pipelines.common.frescura import (
    FICHEROS_CON_FECHA,
    MAX_HORAS_SIN_REGENERAR,
)

#: Huecos maximos medidos entre escrituras reales, en horas. Se actualizan
#: midiendo `git log -- site/<fichero>`, no a ojo.
MAXIMO_MEDIDO: dict[str, float] = {
    "observados.json": 12.8,
}


def test_el_umbral_deja_holgura_sobre_el_maximo_medido() -> None:
    """Un umbral por debajo de lo que el fichero ya hizo es una alarma falsa.

    No se pide un margen enorme: se pide que el limite no este **por debajo**
    de un comportamiento que ya se observo y que era correcto.
    """
    for fichero, maximo in MAXIMO_MEDIDO.items():
        limite = MAX_HORAS_SIN_REGENERAR[fichero]
        assert limite > maximo, (
            f"{fichero}: el umbral son {limite} h y el hueco real mas largo "
            f"medido fue {maximo} h. La alarma saltaria sin que pase nada."
        )


def test_el_latido_conserva_un_umbral_estrecho() -> None:
    """`status.json` sí se escribe siempre, así que su silencio sí es una avería.

    Aflojarlo por simetría con los demás sería justo el error contrario:
    tapar la señal de que el vigía se paró, que es el modo de falla más
    probable de todo el sistema.
    """
    assert MAX_HORAS_SIN_REGENERAR["status.json"] <= 12.0


def test_todo_fichero_con_fecha_tiene_umbral() -> None:
    """Un fichero que declara cuándo se generó y nadie vigila es media guardia."""
    sin_umbral = sorted(set(FICHEROS_CON_FECHA) - set(MAX_HORAS_SIN_REGENERAR))
    assert not sin_umbral, f"declaran fecha y nadie los vigila: {sin_umbral}"


def test_todo_umbral_vigila_un_fichero_que_declara_fecha() -> None:
    """Y al revés: un umbral sobre un fichero sin fecha no comprueba nada.

    `revisar_vejez` lee `generado_utc` de dentro del fichero; si no lo trae, el
    umbral existe y no se aplica nunca — un cero silencioso con forma de
    configuración.
    """
    huerfanos = sorted(set(MAX_HORAS_SIN_REGENERAR) - set(FICHEROS_CON_FECHA))
    assert not huerfanos, f"tienen umbral y no declaran fecha: {huerfanos}"
