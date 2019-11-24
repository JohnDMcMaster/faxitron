from faxitron import xray
import argparse

def run():
    pass

def main():
    parser = argparse.ArgumentParser(description='Decode a .bin to a .png')
    parser.add_argument('--verbose', action="store_true")
    args = parser.parse_args()

    xr = xray.XRay(verbose=args.verbose)
    print("Device %s, version %s" % (xr.get_device(), xr.get_revision()))
    print("Front panel mode: %s " % xr.get_mode())

    if 0:
        xr.set_kvp(10)
        print("kVp: %u" % xr.get_kvp())
        
        xr.set_kvp(35)
        print("kVp: %u" % xr.get_kvp())
    
    
    print('Done')

if __name__ == "__main__":
    main()
