from fastapi import APIRouter, Depends, HTTPException, Request, Response, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import timedelta, datetime
from typing import Optional, List

from database import get_db
from models import User, UserAvatar
from auth import get_current_user, create_access_token
from schemas import UserResponse
from utils_cloudinary import upload_image, delete_image

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Получить информацию о текущем авторизованном пользователе
    """
    # Получаем основной аватар пользователя (если есть) - используем явный запрос вместо lazy loading
    avatar_url = None
    
    # Получаем пользователя с активной сессией
    user_with_session = db.query(User).filter(User.id == current_user.id).first()
    
    if user_with_session:
        # Загружаем аватары пользователя (если есть)
        avatars = db.query(UserAvatar).filter(UserAvatar.user_id == user_with_session.id).all()
        
        if avatars:
            # Ищем основной аватар со статусом approved
            main_avatar = next((avatar for avatar in avatars 
                                if avatar.is_main == 1 and avatar.is_approved == 1), None)
            if main_avatar:
                avatar_url = main_avatar.file_path
            else:
                # Если основного нет, берем первый approved
                approved_avatar = next((avatar for avatar in avatars 
                                       if avatar.is_approved == 1), None)
                if approved_avatar:
                    avatar_url = approved_avatar.file_path
    
    # Если аватар не найден, используем стандартный в зависимости от роли
    if not avatar_url:
        if user_with_session.role == "superadmin":
            avatar_url = "/static/menu/img/manager.png"
        elif user_with_session.role == "admin":
            avatar_url = "/static/menu/img/ska.png"
        else:
            avatar_url = "/static/menu/img/avatar.png"
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "avatar_url": avatar_url,
        "created_at": getattr(current_user, 'created_at', None),
        "updated_at": getattr(current_user, 'updated_at', None)
    }

@router.patch("/update/username")
async def update_username(
    request: Request,
    response: Response,
    username_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновить имя пользователя
    """
    if "username" not in username_data:
        raise HTTPException(status_code=400, detail="Username is required")
    
    new_username = username_data["username"]
    
    # Проверка, не занято ли имя пользователя
    existing_user = db.query(User).filter(User.username == new_username, User.id != current_user.id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Получаем пользователя из текущей сессии для обновления
    user_to_update = db.query(User).filter(User.id == current_user.id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Обновляем имя пользователя
    user_to_update.username = new_username
    db.commit()
    db.refresh(user_to_update)
    
    # Создаем новый токен с обновленным именем пользователя
    access_token_expires = timedelta(minutes=60 * 24 * 7)  # 7 дней
    access_token = create_access_token(
        data={"sub": new_username, "id": user_to_update.id, "role": user_to_update.role, "email": user_to_update.email},
        expires_delta=access_token_expires
    )
    
    # Обновляем токен в куках
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True, 
        max_age=60*60*24*7,  # 7 дней
        samesite="lax"
    )
    
    return {"message": "Username updated successfully", "username": new_username}

@router.patch("/update/password")
async def update_password(
    request: Request,
    password_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновить пароль пользователя
    """
    if "current_password" not in password_data or "new_password" not in password_data:
        raise HTTPException(status_code=400, detail="Current password and new password are required")
    
    # Получаем пользователя из текущей сессии для обновления
    user_to_update = db.query(User).filter(User.id == current_user.id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Проверка текущего пароля
    if not user_to_update.verify_password(password_data["current_password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Обновляем пароль
    user_to_update.hashed_password = User.get_password_hash(password_data["new_password"])
    db.commit()
    
    return {"message": "Password updated successfully"}

@router.post("/password/reset")
async def reset_password(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Инициировать процесс сброса пароля
    """
    # В реальном приложении здесь должна быть отправка email с ссылкой для сброса пароля
    # Для упрощения в тестовой версии просто возвращаем ответ об успехе
    
    # Получаем пользователя из текущей сессии
    user_to_reset = db.query(User).filter(User.id == current_user.id).first()
    if not user_to_reset:
        raise HTTPException(status_code=404, detail="User not found")
    
    # В реальном приложении здесь генерируется токен сброса пароля,
    # сохраняется в базе и отправляется по email
    
    # Имитируем успешную отправку
    return {"message": "Password reset link has been sent to your email"}

@router.get("/avatars", response_model=List[dict])
async def get_user_avatars(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить список всех аватаров пользователя
    """
    avatars = db.query(UserAvatar).filter(UserAvatar.user_id == current_user.id).all()
    
    return [
        {
            "id": avatar.id,
            "file_path": avatar.file_path,
            "is_main": avatar.is_main == 1,
            "is_approved": avatar.is_approved == 1,
            "created_at": avatar.created_at
        }
        for avatar in avatars
    ]

@router.post("/avatars/upload")
async def upload_user_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Загрузить новый аватар пользователя
    """
    # Проверяем тип файла
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Загружаем файл в Cloudinary
        url, public_id = upload_image(await file.read())
        
        if not url or not public_id:
            raise HTTPException(status_code=500, detail="Failed to upload avatar")
        
        # Создаем запись об аватаре в базе данных
        new_avatar = UserAvatar(
            user_id=current_user.id,
            file_path=url,
            cloudinary_public_id=public_id,  # Теперь сохраняем public_id
            is_approved=1,  # Автоматически подтверждаем для пользователя
            request_type='upload',
            request_status='approved'
        )
        
        # Проверяем, есть ли у пользователя основной аватар
        has_main = db.query(UserAvatar).filter(
            UserAvatar.user_id == current_user.id,
            UserAvatar.is_main == 1
        ).first() is not None

        # Если это первый аватар, делаем его основным
        if not has_main:
            new_avatar.is_main = 1
        
        db.add(new_avatar)
        db.commit()
        db.refresh(new_avatar)
        
        return {
            "id": new_avatar.id,
            "file_path": new_avatar.file_path,
            "is_main": new_avatar.is_main == 1,
            "is_approved": new_avatar.is_approved == 1,
            "message": "Avatar uploaded successfully"
        }
    except Exception as e:
        # Логируем ошибку для отладки
        print(f"Error uploading avatar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {str(e)}")

@router.patch("/avatars/{avatar_id}/set-main")
async def set_avatar_as_main(
    request: Request,
    avatar_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Установить аватар как основной
    """
    # Проверяем, существует ли аватар и принадлежит ли он пользователю
    avatar = db.query(UserAvatar).filter(
        UserAvatar.id == avatar_id,
        UserAvatar.user_id == current_user.id
    ).first()
    
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found or not owned by user")
    
    if avatar.is_approved != 1:
        raise HTTPException(status_code=400, detail="Avatar is not approved")
    
    # Сначала снимаем флаг основного аватара со всех аватаров пользователя
    db.query(UserAvatar).filter(
        UserAvatar.user_id == current_user.id
    ).update({"is_main": 0})
    
    # Устанавливаем текущий аватар как основной
    avatar.is_main = 1
    db.commit()
    
    return {"message": "Avatar set as main successfully"}

@router.delete("/avatars/{avatar_id}")
async def delete_user_avatar(
    request: Request,
    avatar_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удалить аватар пользователя
    """
    # Проверяем, существует ли аватар и принадлежит ли он пользователю
    avatar = db.query(UserAvatar).filter(
        UserAvatar.id == avatar_id,
        UserAvatar.user_id == current_user.id
    ).first()
    
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found or not owned by user")
    
    # Если удаляемый аватар был основным, нужно выбрать другой аватар как основной
    was_main = avatar.is_main == 1
    
    # Если у аватара есть public_id в Cloudinary, удаляем изображение из Cloudinary
    if hasattr(avatar, 'cloudinary_public_id') and avatar.cloudinary_public_id:
        delete_image(avatar.cloudinary_public_id)
    
    # Удаляем из базы данных
    db.delete(avatar)
    db.commit()
    
    # Если удаленный аватар был основным, устанавливаем следующий доступный как основной
    if was_main:
        next_avatar = db.query(UserAvatar).filter(
            UserAvatar.user_id == current_user.id,
            UserAvatar.is_approved == 1
        ).first()
        
        if next_avatar:
            next_avatar.is_main = 1
            db.commit()
    
    return {"message": "Avatar deleted successfully"}