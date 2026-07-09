from PIL import Image
import io
from django.core.files.base import ContentFile
from django.utils import timezone
import os

def process_profile_image(image_file, user_id):
    """
    Process and optimize profile image upload
    """
    try:
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large (max 800x800)
        max_size = (800, 800)
        if img.width > max_size[0] or img.height > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save to bytes as JPEG for consistency
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG', quality=85, optimize=True)
        img_content = ContentFile(img_io.getvalue())
        
        # Generate filename
        timestamp = int(timezone.now().timestamp())
        filename = f"user_{user_id}_{timestamp}.jpg"
        
        return filename, img_content
        
    except Exception as e:
        # If image processing fails, use original
        timestamp = int(timezone.now().timestamp())
        file_extension = os.path.splitext(image_file.name)[1]
        filename = f"user_{user_id}_{timestamp}{file_extension}"
        return filename, image_file


def get_user_stats(user):
    """
    Get comprehensive user statistics
    """
    stats = {
        'profile_completion': 0,
        'role_specific': {}
    }
    
    # Calculate profile completion
    total_fields = 0
    filled_fields = 0
    
    # User model fields
    user_fields = ['first_name', 'last_name', 'email', 'phone_number', 'gender', 'bio', 'profile_pic']
    for field in user_fields:
        total_fields += 1
        value = getattr(user, field)
        if value and (field != 'profile_pic' or value != 'profile_pics/default.png'):
            filled_fields += 1
    
    # Check role-specific profile
    if user.is_student and hasattr(user, 'student_profile'):
        student = user.student_profile
        student_fields = ['date_of_birth', 'level', 'institution', 'student_id_number']
        for field in student_fields:
            total_fields += 1
            if getattr(student, field):
                filled_fields += 1
    
    if total_fields > 0:
        stats['profile_completion'] = int((filled_fields / total_fields) * 100)
    
    return stats