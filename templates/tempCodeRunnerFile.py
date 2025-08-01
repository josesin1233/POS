from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

inventario = {
    "001": {"nombre": "Paleta", "precio": 2, "stock": 25},
    "002": {"nombre": "Chetos", "precio": 10, "stock": 15},
    "003": {"nombre": "Coca", "precio": 20, "stock": 50}
}

carrito = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/producto", methods=["POST"])
def obtener_producto():
    data = request.json
    codigo = data.get("codigo")
    nombre = data.get("nombre")

    for cod, prod in inventario.items():
        if (codigo and codigo == cod) or (nombre and prod["nombre"].lower() == nombre.lower()):
            return jsonify({"codigo": cod, **prod})

    return jsonify({"error": "Producto no encontrado"}), 404

@app.route("/inventario", methods=["GET"])
def mostrar_inventario():
    # Muestra la página HTML del inventario (sin datos)
    return render_template("inventario.html")

@app.route("/api/inventario", methods=["GET"])
def obtener_inventario_json():
    # Devuelve el inventario en formato JSON para la tabla
    lista_productos = [{"codigo": codigo, **producto} for codigo, producto in inventario.items()]
    return jsonify(lista_productos)

@app.route("/inventario", methods=["POST"])
def nuevo_producto():
    data = request.json
    codigo = data.get("codigo")
    nombre = data.get("nombre")
    precio = data.get("precio")
    stock = data.get("stock")

    if not all([codigo, nombre]) or precio is None or stock is None:
        return jsonify({"error": "Faltan campos o hay datos inválidos"}), 400

    if codigo in inventario:
        return jsonify({"error": "Código ya existente"}), 400

    try:
        precio = float(precio)
        stock = int(stock)
    except ValueError:
        return jsonify({"error": "Precio o stock no son válidos"}), 400

    inventario[codigo] = {
        "nombre": nombre,
        "precio": precio,
        "stock": stock
    }

    return jsonify({"mensaje": "Producto agregado correctamente", "inventario": inventario})

if __name__ == "__main__":
    app.run(debug=True)
