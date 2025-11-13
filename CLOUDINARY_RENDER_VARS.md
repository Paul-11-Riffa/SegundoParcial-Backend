# 🔑 Variables de Cloudinary para Render

## ✅ COPIA Y PEGA ESTAS 4 VARIABLES EN RENDER

Ve a: **Render Dashboard** → **segundoparcial-backend** → **Environment**

Click en **"Add Environment Variable"** y agrega estas 4 variables:

---

### Variable 1:
```
Key: CLOUDINARY_CLOUD_NAME
Value: Root
```

---

### Variable 2:
```
Key: CLOUDINARY_API_KEY
Value: 914214314924374
```

---

### Variable 3:
```
Key: CLOUDINARY_API_SECRET
Value: xhl9yhqzufA7J1w8XzNYTPHqsNY
```

---

### Variable 4:
```
Key: CLOUDINARY_URL
Value: cloudinary://914214314924374:xhl9yhqzufA7J1w8XzNYTPHqsNY@Root
```

---

## 📝 Nota sobre Cloud Name

Si "Root" no es el Cloud Name correcto:

1. Ve a tu Dashboard de Cloudinary
2. En la parte superior verás: **Cloud name: xxxxxxx**
3. Usa ese valor en lugar de "Root"
4. También actualiza la CLOUDINARY_URL con el Cloud Name correcto

---

## ✅ Después de agregar las variables:

1. Click en **"Save Changes"** en Render
2. Espera que redesplegue (automático, 3-5 min)
3. ¡Listo! Las imágenes ahora se servirán desde Cloudinary

---

## 🎯 Próximo Paso

Después de configurar en Render, haz commit y push:

```powershell
git add .
git commit -m "Add Cloudinary configuration for media storage"
git push origin main
```

Render detectará el cambio y redesplegará automáticamente.
