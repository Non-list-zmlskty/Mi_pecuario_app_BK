import apiClient from '@/api/apiClient';

// Función para obtener las fichas del usuario
export const getMisFichas = async () => {
  // Asegúrate de NO duplicar el prefijo /api/
  return await apiClient.get('/api/animal/mis-fichas');
};

// Otras funciones relacionadas con las fichas de animales...