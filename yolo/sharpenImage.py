import cv2 as cv


def sharpen(img, sigma=100):
    # sigma = 5、15、25
    blur_img = cv.GaussianBlur(img, (0, 0), sigma)
    usm = cv.addWeighted(img, 1.5, blur_img, -0.5, 0)

    return usm

if __name__ == "__main__":
    image_path = f"TrainingAndTestData/image-5.png"


    # for i in range(1, 100, 10):
    img = cv.imread(image_path)
    print(img.shape)
    new_img = sharpen(img, sigma = 20)
    print(new_img.shape)

    cv.imshow("orgImg", img)
    cv.imshow("newImg", new_img)
    cv.waitKey(0)
    cv.destroyAllWindows()