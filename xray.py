from faxitron import xray
import argparse

def run():
    pass

def main():
    parser = argparse.ArgumentParser(description='Decode a .bin to a .png')
    #parser.add_argument('fin', help='.bin file name in')
    args = parser.parse_args()

    xr = xray.XRay()
    print(xr.get_kvp())
    xr.set_kvp(15)

    print('Done')

if __name__ == "__main__":
    main()
